# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Upload Router (MinIO upload, file validation, queueing)
# ═══════════════════════════════════════════════════════════════════
import hashlib
import io
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory, get_db
from app.models import InboundFile, ParsedDocument, ParsedLineItem
from app.routers.auth import get_current_user
from app.services.minio_client import download_bytes, upload_bytes
from app.services.parse_document_service import parse_document, ParseResult

router = APIRouter(prefix="/api/v1/upload", tags=["Upload"])

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "text/xml": "xml",
    "application/xml": "xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
    "image/jpeg": "img",
    "image/png": "img",
    "image/webp": "img",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class UploadResponse(BaseModel):
    id: str
    file_type: str
    original_filename: str
    sha256: str
    object_key: str


async def _process_upload_parsing(
    inbound_file_id: str,
    company_id: str,
    file_type: str,
    object_key: str,
    supplier_id: Optional[str],
):
    """Background task to parse an uploaded file."""
    from uuid import UUID
    # Create a new DB session for this background task
    async with async_session_factory() as db:
        try:
            # Download file content from MinIO
            content = download_bytes(object_key)
            # Parse the document
            parse_result: ParseResult = await parse_document(
                content=content,
                file_type=file_type,
                supplier_id=UUID(supplier_id) if supplier_id else None,
                db=db,
            )
            # Create ParsedDocument record
            parsed_doc = ParsedDocument(
                company_id=UUID(company_id),
                inbound_file_id=UUID(inbound_file_id),
                doc_kind=parse_result.doc_kind,
                parse_status="success" if parse_result.error_message is None and parse_result.confidence >= 0.0 and parse_result.lines else "failed",
                parser_version=parse_result.parser_version,
                confidence_score=parse_result.confidence if parse_result.confidence is not None else None,
                header_json=parse_result.header_json or {},
            )
            db.add(parsed_doc)
            await db.flush()  # to get ID
            # Create line items if any
            for line_dict in parse_result.lines:
                line_item = ParsedLineItem(
                    company_id=UUID(company_id),
                    parsed_document_id=parsed_doc.id,
                    line_index=line_dict.get("line_index", 0),
                    supplier_sku_raw=line_dict.get("supplier_sku_raw"),
                    supplier_sku_normalized=line_dict.get("supplier_sku_normalized"),
                    description_raw=line_dict.get("description_raw"),
                    qty=line_dict.get("qty"),
                    unit_price=line_dict.get("unit_price"),
                    line_total=line_dict.get("line_total"),
                    vat_rate=line_dict.get("vat_rate"),
                    extraction_source=line_dict.get("extraction_source", "unknown"),
                    extraction_notes=line_dict.get("extraction_notes"),
                )
                db.add(line_item)
            await db.commit()
        except Exception as e:
            # In case of any unexpected error, we still want to record a failed parsed document
            async with async_session_factory() as db2:
                try:
                    parsed_doc = ParsedDocument(
                        company_id=UUID(company_id),
                        inbound_file_id=UUID(inbound_file_id),
                        doc_kind="unknown",
                        parse_status="failed",
                        parser_version="unknown",
                        confidence_score=None,
                        header_json={"error": str(e)},
                    )
                    db2.add(parsed_doc)
                    await db2.commit()
                except Exception:
                    pass  # Avoid infinite error loops


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    supplier_id: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a file to MinIO and create an InboundFile record, then trigger parsing in background."""
    from uuid import UUID, uuid4

    # Validate file type
    content_type = file.content_type or ""
    file_type = ALLOWED_TYPES.get(content_type)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Allowed: pdf, xml, xlsx, img"
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Compute SHA256
    sha256 = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = await db.execute(
        select(InboundFile).where(InboundFile.sha256 == sha256)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="File already uploaded (duplicate SHA256)")

    # Generate object key
    object_key = f"raw-uploads/{current_user.company_id}/{uuid4()}/{file.filename}"

    # Upload to MinIO
    try:
        upload_bytes(content, object_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MinIO upload failed: {exc}")

    # Create InboundFile record
    inbound_file = InboundFile(
        company_id=current_user.company_id,
        file_type=file_type,
        object_key=object_key,
        sha256=sha256,
        original_filename=file.filename,
        uploaded_by=current_user.id,
    )
    if supplier_id:
        inbound_file.supplier_id = UUID(supplier_id)

    db.add(inbound_file)
    await db.commit()
    await db.refresh(inbound_file)

    # Trigger background parsing
    background_tasks.add_task(
        _process_upload_parsing,
        str(inbound_file.id),
        str(current_user.company_id),
        file_type,
        object_key,
        str(supplier_id) if supplier_id else None,
    )

    return UploadResponse(
        id=str(inbound_file.id),
        file_type=inbound_file.file_type,
        original_filename=inbound_file.original_filename or "",
        sha256=inbound_file.sha256,
        object_key=inbound_file.object_key,
    )