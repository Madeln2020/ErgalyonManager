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


if __name__ == "__main__":
    celery_app.start()
