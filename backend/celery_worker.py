"""
EDM v2.1 — Celery Worker
Background task queue for document parsing, enrichment, etc.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional
from uuid import UUID

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from app.config import settings

logger = logging.getLogger("edm.celery")

# ── Celery configuration ──────────────────────────────────────────
celery_app = Celery(
    "edm_v2_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Athens",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ── Sync DB session for Celery (must use sync driver) ─────────────
# Celery tasks run synchronously, so we use psycopg2 (sync) for DB access.
_SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
_sync_engine = create_engine(_SYNC_DB_URL, echo=False)
SyncSessionLocal = sessionmaker(_sync_engine, expire_on_commit=False)


# ── Async DB session (for enrich task) ────────────────────────────
_async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(_async_engine, class_=AsyncSession, expire_on_commit=False)


# ════════════════════════════════════════════════════════════════════
# Task: parse_document
# ════════════════════════════════════════════════════════════════════
@celery_app.task(name="parse_document", bind=True, max_retries=2, default_retry_delay=30)
def parse_document_task(self, inbound_file_id: str):
    """
    Background task: parse an uploaded document.

    1. Retrieve InboundFile from DB.
    2. Download file from MinIO.
    3. Select parser based on file_type and supplier.default_parser.
    4. Run parser → get structured data.
    5. Save ParsedDocument + ParsedLineItem records.
    6. Update parse_status.
    """
    from app.models import InboundFile, ParsedDocument, ParsedLineItem, Supplier
    from app.services.minio_client import download_bytes, RAW_UPLOADS_BUCKET
    from app.services.parse_document_service import parse_document_sync

    logger.info("parse_document started for inbound_file_id=%s", inbound_file_id)

    with SyncSessionLocal() as db:
        try:
            # 1. Retrieve InboundFile
            result = db.execute(
                select(InboundFile).where(InboundFile.id == UUID(inbound_file_id))
            )
            inbound_file = result.scalar_one_or_none()
            if inbound_file is None:
                logger.error("InboundFile %s not found", inbound_file_id)
                return {"status": "error", "error": "InboundFile not found"}

            # Get supplier default_parser if available
            supplier_parser = None
            if inbound_file.supplier_id:
                supplier_result = db.execute(
                    select(Supplier).where(Supplier.id == inbound_file.supplier_id)
                )
                supplier = supplier_result.scalar_one_or_none()
                if supplier and supplier.default_parser:
                    supplier_parser = supplier.default_parser

            # Create a ParsedDocument record (pending)
            parsed_doc = ParsedDocument(
                company_id=inbound_file.company_id,
                inbound_file_id=inbound_file.id,
                doc_kind="unknown",
                parse_status="pending",
                parser_version="",
                confidence_score=None,
                header_json=None,
            )
            db.add(parsed_doc)
            db.flush()

            # 2. Download file from MinIO
            content = download_bytes(inbound_file.object_key, bucket=RAW_UPLOADS_BUCKET)

            # 3-4. Parse document
            parse_result = parse_document_sync(
                content=content,
                file_type=inbound_file.file_type,
                supplier_parser=supplier_parser,
            )

            if parse_result.error_message:
                parsed_doc.parse_status = "failed"
                parsed_doc.header_json = {"error": parse_result.error_message}
                db.commit()
                logger.warning(
                    "parse_document failed for %s: %s",
                    inbound_file_id,
                    parse_result.error_message,
                )
                return {
                    "status": "failed",
                    "inbound_file_id": inbound_file_id,
                    "error": parse_result.error_message,
                }

            # 5. Update ParsedDocument
            parsed_doc.doc_kind = parse_result.doc_kind
            parsed_doc.parse_status = "success"
            parsed_doc.parser_version = parse_result.parser_version
            parsed_doc.confidence_score = parse_result.confidence
            parsed_doc.header_json = parse_result.header_json or {}

            # 6. Save ParsedLineItem records
            for line_data in parse_result.lines:
                extraction_source = line_data.pop("extraction_source", "xml")
                line_item = ParsedLineItem(
                    company_id=inbound_file.company_id,
                    parsed_document_id=parsed_doc.id,
                    line_index=line_data.get("line_index", 0),
                    supplier_sku_raw=line_data.get("supplier_sku_raw"),
                    description_raw=line_data.get("description_raw"),
                    qty=line_data.get("qty"),
                    unit_price=line_data.get("unit_price"),
                    line_total=line_data.get("line_total"),
                    vat_rate=line_data.get("vat_rate"),
                    extraction_source=extraction_source,
                    extraction_notes=line_data.get("extraction_notes"),
                )
                db.add(line_item)

            db.commit()
            logger.info(
                "parse_document success for %s: kind=%s confidence=%.1f lines=%d",
                inbound_file_id,
                parse_result.doc_kind,
                parse_result.confidence,
                len(parse_result.lines),
            )
            return {
                "status": "success",
                "inbound_file_id": inbound_file_id,
                "doc_kind": parse_result.doc_kind,
                "confidence": parse_result.confidence,
                "line_count": len(parse_result.lines),
            }

        except Exception as exc:
            db.rollback()
            logger.exception("parse_document exception for %s: %s", inbound_file_id, exc)
            # Mark as failed
            try:
                result = db.execute(
                    select(InboundFile).where(InboundFile.id == UUID(inbound_file_id))
                )
                inbound_file = result.scalar_one_or_none()
                if inbound_file:
                    # Check if parsed_doc exists
                    pd_result = db.execute(
                        select(ParsedDocument).where(
                            ParsedDocument.inbound_file_id == inbound_file.id
                        )
                    )
                    parsed_doc = pd_result.scalar_one_or_none()
                    if parsed_doc:
                        parsed_doc.parse_status = "failed"
                        parsed_doc.header_json = {"error": str(exc)}
                        db.commit()
            except Exception:
                pass

            # Retry on transient errors
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                pass

            return {"status": "error", "error": str(exc)}


# ════════════════════════════════════════════════════════════════════
# Task: enrich_product (existing from Phase 3)
# ════════════════════════════════════════════════════════════════════
@celery_app.task(name="enrich_product")
async def enrich_product_task(product_id: str, context: str):
    async with AsyncSessionLocal() as db:
        from app.services.rag_service import RAGService
        service = RAGService(db)
        await service.enrich(product_id, context)
        return {"status": "ok", "product_id": product_id}


# ════════════════════════════════════════════════════════════════════
# Task: generate_export
# ════════════════════════════════════════════════════════════════════
@celery_app.task(name="generate_export", bind=True, max_retries=2, default_retry_delay=30)
def generate_export(self, export_job_id: str):
    """Background task: generate an export file asynchronously.

    Creates the export file, saves to EXPORT_OUTPUT_DIR, updates the
    ExportJob record with status, total_rows, object_key, and completed_at.
    """
    import io
    import csv
    import json
    import os
    from datetime import datetime, timezone

    from app.models import (
        ExportJob, Product, CostUpdate, ProductSupplierLink,
        User, Supplier,
    )
    from app.config import settings

    logger.info("generate_export started for export_job_id=%s", export_job_id)

    with SyncSessionLocal() as db:
        try:
            # 1. Retrieve ExportJob
            job = db.query(ExportJob).filter(ExportJob.id == UUID(export_job_id)).first()
            if job is None:
                logger.error("ExportJob %s not found", export_job_id)
                return {"status": "error", "error": "ExportJob not found"}

            # 2. Update status to processing
            job.status = "processing"
            db.commit()

            # 3. Build export data
            headers = []
            rows = []
            total_rows = 0
            filename = "export"

            if job.export_type == "products":
                items = db.query(Product).filter(Product.is_deleted == False).limit(10000).all()
                headers = ["id", "canonical_name", "internal_code", "category_path", "status"]
                rows = [
                    [str(p.id), p.canonical_name, p.internal_code, p.category_path, p.status]
                    for p in items
                ]
                filename = "products_export"
                total_rows = len(items)

            elif job.export_type == "costs":
                rows_data = (
                    db.query(CostUpdate, Product, ProductSupplierLink, User, Supplier)
                    .join(Product, CostUpdate.product_id == Product.id)
                    .join(ProductSupplierLink, CostUpdate.product_supplier_link_id == ProductSupplierLink.id)
                    .join(User, CostUpdate.approved_by == User.id, isouter=True)
                    .join(Supplier, ProductSupplierLink.supplier_id == Supplier.id, isouter=True)
                    .filter(CostUpdate.status == "approved")
                    .order_by(CostUpdate.approved_at.desc())
                    .limit(10000)
                    .all()
                )
                headers = [
                    "cost_update_id", "product_id", "product_name",
                    "supplier_id", "supplier_name", "old_cost", "new_cost",
                    "source", "source_ref", "approved_by", "approved_at", "created_at",
                ]
                rows = []
                for cu, product, link, user, supplier in rows_data:
                    rows.append([
                        str(cu.id),
                        str(product.id),
                        product.canonical_name,
                        str(link.supplier_id) if link.supplier_id else "",
                        supplier.name if supplier else "",
                        float(cu.old_cost) if cu.old_cost else None,
                        float(cu.new_cost) if cu.new_cost else None,
                        cu.source,
                        cu.source_ref or "",
                        str(user.id) if user else "",
                        cu.approved_at.isoformat() if cu.approved_at else "",
                        cu.created_at.isoformat() if cu.created_at else "",
                    ])
                filename = "costs_export"
                total_rows = len(rows_data)

            elif job.export_type == "suppliers":
                items = db.query(Supplier).filter(Supplier.is_deleted == False).limit(10000).all()
                headers = ["id", "name", "vat_number", "default_currency", "is_active"]
                rows = [
                    [str(s.id), s.name, s.vat_number or "", s.default_currency, s.is_active]
                    for s in items
                ]
                filename = "suppliers_export"
                total_rows = len(items)

            else:
                job.status = "failed"
                job.error_message = f"Unsupported export type: {job.export_type}"
                db.commit()
                return {"status": "failed", "error": job.error_message}

            # 4. Generate file
            content_bytes = None
            content_str = None
            ext = job.file_format

            if ext == "csv":
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(headers)
                writer.writerows(rows)
                content_str = output.getvalue()
                content_bytes = content_str.encode("utf-8-sig")

            elif ext == "json":
                data_dicts = []
                if job.export_type == "products":
                    for p in db.query(Product).filter(Product.is_deleted == False).limit(10000).all():
                        data_dicts.append({
                            "id": str(p.id), "canonical_name": p.canonical_name,
                            "internal_code": p.internal_code, "category_path": p.category_path,
                            "status": p.status,
                        })
                elif job.export_type == "costs":
                    for cu, product, link, user, supplier in rows_data:
                        data_dicts.append({
                            "cost_update_id": str(cu.id), "product_id": str(product.id),
                            "product_name": product.canonical_name,
                            "supplier_id": str(link.supplier_id) if link.supplier_id else None,
                            "supplier_name": supplier.name if supplier else None,
                            "old_cost": float(cu.old_cost) if cu.old_cost else None,
                            "new_cost": float(cu.new_cost) if cu.new_cost else None,
                            "source": cu.source, "source_ref": cu.source_ref,
                            "approved_by": str(user.id) if user else None,
                            "approved_at": cu.approved_at.isoformat() if cu.approved_at else None,
                            "created_at": cu.created_at.isoformat() if cu.created_at else None,
                        })
                elif job.export_type == "suppliers":
                    for s in db.query(Supplier).filter(Supplier.is_deleted == False).limit(10000).all():
                        data_dicts.append({
                            "id": str(s.id), "name": s.name, "vat_number": s.vat_number,
                            "default_currency": s.default_currency, "is_active": s.is_active,
                        })
                content_str = json.dumps(data_dicts, indent=2, default=str)
                content_bytes = content_str.encode("utf-8")

            elif ext == "xml":
                xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', f'<{job.export_type}>']
                if job.export_type == "products":
                    for p in db.query(Product).filter(Product.is_deleted == False).limit(10000).all():
                        xml_lines.append(f"  <product>")
                        xml_lines.append(f"    <id>{p.id}</id>")
                        xml_lines.append(f"    <canonical_name>{p.canonical_name}</canonical_name>")
                        xml_lines.append(f"    <internal_code>{p.internal_code}</internal_code>")
                        xml_lines.append(f"    <category_path>{p.category_path or ''}</category_path>")
                        xml_lines.append(f"    <status>{p.status}</status>")
                        xml_lines.append(f"  </product>")
                elif job.export_type == "costs":
                    for cu, product, link, user, supplier in rows_data:
                        xml_lines.append(f"  <cost_update>")
                        xml_lines.append(f"    <id>{cu.id}</id>")
                        xml_lines.append(f"    <product_id>{product.id}</product_id>")
                        xml_lines.append(f"    <product_name>{product.canonical_name}</product_name>")
                        xml_lines.append(f"    <supplier_id>{link.supplier_id if link.supplier_id else ''}</supplier_id>")
                        xml_lines.append(f"    <supplier_name>{supplier.name if supplier else ''}</supplier_name>")
                        xml_lines.append(f"    <old_cost>{cu.old_cost if cu.old_cost else ''}</old_cost>")
                        xml_lines.append(f"    <new_cost>{cu.new_cost if cu.new_cost else ''}</new_cost>")
                        xml_lines.append(f"    <source>{cu.source}</source>")
                        xml_lines.append(f"    <source_ref>{cu.source_ref or ''}</source_ref>")
                        xml_lines.append(f"    <approved_by>{user.id if user else ''}</approved_by>")
                        xml_lines.append(f"    <approved_at>{cu.approved_at.isoformat() if cu.approved_at else ''}</approved_at>")
                        xml_lines.append(f"    <created_at>{cu.created_at.isoformat() if cu.created_at else ''}</created_at>")
                        xml_lines.append(f"  </cost_update>")
                elif job.export_type == "suppliers":
                    for s in db.query(Supplier).filter(Supplier.is_deleted == False).limit(10000).all():
                        xml_lines.append(f"  <supplier>")
                        xml_lines.append(f"    <id>{s.id}</id>")
                        xml_lines.append(f"    <name>{s.name}</name>")
                        xml_lines.append(f"    <vat_number>{s.vat_number or ''}</vat_number>")
                        xml_lines.append(f"    <default_currency>{s.default_currency}</default_currency>")
                        xml_lines.append(f"    <is_active>{s.is_active}</is_active>")
                        xml_lines.append(f"  </supplier>")
                xml_lines.append(f"</{job.export_type}>")
                content_str = "\n".join(xml_lines)
                content_bytes = content_str.encode("utf-8")

            elif ext == "xlsx":
                try:
                    import openpyxl
                except ImportError:
                    job.status = "failed"
                    job.error_message = "XLSX export not available (openpyxl not installed)"
                    db.commit()
                    return {"status": "failed", "error": job.error_message}

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = job.export_type.capitalize()
                ws.append(headers)
                for row in rows:
                    ws.append(row)
                output = io.BytesIO()
                wb.save(output)
                content_bytes = output.getvalue()

            else:
                job.status = "failed"
                job.error_message = f"Unsupported file format: {ext}"
                db.commit()
                return {"status": "failed", "error": job.error_message}

            # 5. Save to export output directory
            export_dir = getattr(settings, "EXPORT_OUTPUT_DIR", "/tmp/edm_exports")
            os.makedirs(export_dir, exist_ok=True)
            file_ext = ext if ext != "xlsx" else "xlsx"
            file_path = os.path.join(export_dir, f"{export_job_id}.{file_ext}")

            mode = "wb" if ext == "xlsx" or content_bytes else "w"
            if ext == "xlsx":
                with open(file_path, "wb") as f:
                    f.write(content_bytes)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content_str or "")

            # 6. Update job record
            job.status = "completed"
            job.object_key = file_path
            job.total_rows = total_rows
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                "generate_export completed for %s: type=%s format=%s rows=%d file=%s",
                export_job_id, job.export_type, ext, total_rows, file_path,
            )
            return {"status": "completed", "file": file_path, "total_rows": total_rows}

        except Exception as exc:
            db.rollback()
            logger.exception("generate_export exception for %s: %s", export_job_id, exc)
            try:
                job = db.query(ExportJob).filter(ExportJob.id == UUID(export_job_id)).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(exc)
                    db.commit()
            except Exception:
                pass
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                pass
            return {"status": "error", "error": str(exc)}


if __name__ == "__main__":
    celery_app.start()
