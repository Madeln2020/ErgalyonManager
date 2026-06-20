"""
EDM v2.1 — Upload Router (Phase 4: Invoice Intake)

POST /api/v1/upload          — single file upload
POST /api/v1/upload/batch    — batch file upload
GET  /api/v1/upload/{id}     — get upload status
GET  /api/v1/upload/{id}/parse — get parse result for an upload
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_user, User
from app.config import settings
from app.database import get_db
from app.models import (
    Company,
    InboundFile,
    ParsedDocument,
    ParsedLineItem,
    Supplier,
)
from app.schemas.upload import (
    UploadResponse,
    UploadBatchResponse,
    ParseStatusResponse,
)
from app.services.minio_client import upload_bytes, ensure_bucket_exists
from celery_worker import parse_document_task

logger = logging.getLogger("edm.upload")

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

# ── Constants ──────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS
MAX_UPLOAD_SIZE = settings.MAX_UPLOAD_SIZE

EXT_TO_FILE_TYPE = {
    ".pdf": "pdf",
    ".xml": "xml",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".csv": "xlsx",      # treat CSV as xlsx-like
    ".jpg": "img",
    ".jpeg": "img",
    ".png": "img",
    ".tiff": "img",
    ".tif": "img",
}

MINIO_BUCKET = "raw-uploads"


# ── Helpers ────────────────────────────────────────────────────────
def _get_ext(filename: str) -> str:
    """Return lowercase extension including dot."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def _validate_file(filename: str, content: bytes) -> tuple[str, str]:
    """
    Validate file extension and size.
    Returns (extension, file_type) on success.
    Raises HTTPException on failure.
    """
    ext = _get_ext(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    file_type = EXT_TO_FILE_TYPE.get(ext)
    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot map extension '{ext}' to a file type.",
        )
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({len(content)} bytes). Max: {MAX_UPLOAD_SIZE} bytes.",
        )
    return ext, file_type


def _compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def _verify_supplier(
    db: AsyncSession, supplier_id: UUID, company_id: UUID
) -> Supplier:
    """Verify supplier exists and belongs to the user's company."""
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == company_id,
            Supplier.is_active == True,
        )
    )
    supplier = result.scalar_one_or_none()
    if supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier {supplier_id} not found in your company.",
        )
    return supplier


async def _save_upload(
    db: AsyncSession,
    user: User,
    supplier_id: UUID,
    filename: str,
    content: bytes,
) -> InboundFile:
    """
    Validate, upload to MinIO, create InboundFile record, enqueue parse task.
    Returns the InboundFile DB object (not yet committed — caller commits via get_db).
    """
    ext, file_type = _validate_file(filename, content)
    sha256 = _compute_sha256(content)

    # Build MinIO object key:  {supplier_id}/{uuid}_{original_filename}
    object_key = f"{supplier_id}/{uuid4()}{ext}"

    # Dedup check: same company + same sha256 → reject duplicate
    existing = await db.execute(
        select(InboundFile).where(
            InboundFile.company_id == user.company_id,
            InboundFile.sha256 == sha256,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File with SHA256 {sha256[:16]}… already uploaded.",
        )

    # Upload to MinIO
    try:
        upload_bytes(content, object_key, bucket=MINIO_BUCKET)
    except Exception as exc:
        logger.error("MinIO upload failed for %s: %s", object_key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Object storage upload failed. Please try again.",
        )

    # Create DB record
    inbound_file = InboundFile(
        company_id=user.company_id,
        supplier_id=supplier_id,
        file_type=file_type,
        object_key=object_key,
        sha256=sha256,
        original_filename=filename,
        uploaded_by=user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(inbound_file)
    await db.flush()  # assign ID without commit

    # Enqueue Celery task parse_document(inbound_file_id)
    try:
        parse_document_task.delay(str(inbound_file.id))
        logger.info("Enqueued parse_document for inbound_file %s", inbound_file.id)
    except Exception as exc:
        logger.warning("Failed to enqueue parse task for %s: %s", inbound_file.id, exc)
        # We still return success — the file is stored; parsing can be retried.

    return inbound_file


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    supplier_id: UUID = Form(..., description="Supplier UUID"),
    file: UploadFile = File(..., description="File to upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Upload a single file (PDF, XML, XLSX, image).

    - Validates file type and size.
    - Computes SHA256 for dedup.
    - Stores file to MinIO (raw-uploads bucket).
    - Creates InboundFile DB record.
    - Enqueues `parse_document` Celery task.
    - Returns 202 Accepted with upload metadata.
    """
    # Verify supplier ownership
    await _verify_supplier(db, supplier_id, current_user.company_id)

    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"

    inbound_file = await _save_upload(db, current_user, supplier_id, filename, content)

    return UploadResponse(
        id=inbound_file.id,
        company_id=inbound_file.company_id,
        supplier_id=inbound_file.supplier_id,
        file_type=inbound_file.file_type,
        object_key=inbound_file.object_key,
        sha256=inbound_file.sha256,
        original_filename=inbound_file.original_filename,
        uploaded_by=inbound_file.uploaded_by,
        uploaded_at=inbound_file.uploaded_at,
        parse_status="pending",
    )


@router.post("/batch", response_model=UploadBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_batch(
    supplier_id: UUID = Form(..., description="Supplier UUID"),
    files: list[UploadFile] = File(..., description="Files to upload (max 10)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Upload multiple files (max 10) for a supplier.
    Each file is validated and processed individually.
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per batch upload.",
        )

    await _verify_supplier(db, supplier_id, current_user.company_id)

    uploaded = []
    errors = []

    for file in files:
        try:
            content = await file.read()
            filename = file.filename or "unknown"
            inbound_file = await _save_upload(db, current_user, supplier_id, filename, content)
            uploaded.append(
                UploadResponse(
                    id=inbound_file.id,
                    company_id=inbound_file.company_id,
                    supplier_id=inbound_file.supplier_id,
                    file_type=inbound_file.file_type,
                    object_key=inbound_file.object_key,
                    sha256=inbound_file.sha256,
                    original_filename=inbound_file.original_filename,
                    uploaded_by=inbound_file.uploaded_by,
                    uploaded_at=inbound_file.uploaded_at,
                    parse_status="pending",
                )
            )
        except HTTPException as exc:
            errors.append({"filename": file.filename, "detail": exc.detail})
        except Exception as exc:
            errors.append({"filename": file.filename, "detail": str(exc)})

    return UploadBatchResponse(
        uploaded_files=uploaded,
        total_count=len(files),
        success_count=len(uploaded),
        failed_count=len(errors),
        errors=errors,
    )


@router.get("/{inbound_file_id}", response_model=UploadResponse)
async def get_upload_status(
    inbound_file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Retrieve upload metadata by InboundFile ID."""
    result = await db.execute(
        select(InboundFile).where(
            InboundFile.id == inbound_file_id,
            InboundFile.company_id == current_user.company_id,
        )
    )
    inbound_file = result.scalar_one_or_none()
    if inbound_file is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    # Check parse status
    parse_result = await db.execute(
        select(ParsedDocument).where(
            ParsedDocument.inbound_file_id == inbound_file_id,
            ParsedDocument.company_id == current_user.company_id,
        )
    )
    parsed_doc = parse_result.scalar_one_or_none()
    parse_status = parsed_doc.parse_status if parsed_doc else "pending"

    return UploadResponse(
        id=inbound_file.id,
        company_id=inbound_file.company_id,
        supplier_id=inbound_file.supplier_id,
        file_type=inbound_file.file_type,
        object_key=inbound_file.object_key,
        sha256=inbound_file.sha256,
        original_filename=inbound_file.original_filename,
        uploaded_by=inbound_file.uploaded_by,
        uploaded_at=inbound_file.uploaded_at,
        parse_status=parse_status,
    )


@router.get("/{inbound_file_id}/parse", response_model=ParseStatusResponse)
async def get_parse_result(
    inbound_file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Retrieve parsing result for a given upload."""
    # Verify the inbound file belongs to the user's company
    result = await db.execute(
        select(InboundFile).where(
            InboundFile.id == inbound_file_id,
            InboundFile.company_id == current_user.company_id,
        )
    )
    inbound_file = result.scalar_one_or_none()
    if inbound_file is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    # Get parsed document
    parse_result = await db.execute(
        select(ParsedDocument).where(
            ParsedDocument.inbound_file_id == inbound_file_id,
            ParsedDocument.company_id == current_user.company_id,
        )
    )
    parsed_doc = parse_result.scalar_one_or_none()
    if parsed_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parse result yet. Document may still be processing.",
        )

    # Count line items
    count_result = await db.execute(
        select(func.count()).select_from(ParsedLineItem).where(
            ParsedLineItem.parsed_document_id == parsed_doc.id
        )
    )
    line_item_count = count_result.scalar() or 0

    return ParseStatusResponse(
        id=parsed_doc.id,
        inbound_file_id=parsed_doc.inbound_file_id,
        doc_kind=parsed_doc.doc_kind,
        parse_status=parsed_doc.parse_status,
        parser_version=parsed_doc.parser_version,
        confidence_score=parsed_doc.confidence_score,
        header_json=parsed_doc.header_json,
        line_item_count=line_item_count,
        created_at=parsed_doc.created_at,
        updated_at=parsed_doc.updated_at,
    )


@router.post("/{inbound_file_id}/reparse", status_code=status.HTTP_202_ACCEPTED)
async def reparse_upload(
    inbound_file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Re-queue a document for parsing (e.g. after failure)."""
    result = await db.execute(
        select(InboundFile).where(
            InboundFile.id == inbound_file_id,
            InboundFile.company_id == current_user.company_id,
        )
    )
    inbound_file = result.scalar_one_or_none()
    if inbound_file is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    # Reset parse status if exists
    parse_result = await db.execute(
        select(ParsedDocument).where(
            ParsedDocument.inbound_file_id == inbound_file_id,
            ParsedDocument.company_id == current_user.company_id,
        )
    )
    parsed_doc = parse_result.scalar_one_or_none()
    if parsed_doc:
        parsed_doc.parse_status = "pending"
        db.add(parsed_doc)

    # Enqueue again
    try:
        parse_document_task.delay(str(inbound_file.id))
        logger.info("Re-enqueued parse_document for inbound_file %s", inbound_file.id)
    except Exception as exc:
        logger.warning("Failed to re-enqueue parse task for %s: %s", inbound_file.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to enqueue parse task. Please try again later.",
        )

    return {"message": "Re-parse enqueued", "inbound_file_id": str(inbound_file.id)}
