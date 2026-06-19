"""
EDM v2 – Supplier Agreement Router
Handles document upload, full‑text indexing, and RAG search on supplier agreements.
"""

import os
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SupplierAgreement
from app.schemas import (
    SupplierAgreementCreate,
    SupplierAgreementRead,
    SupplierAgreementSearch,
)

router = APIRouter(prefix="/api/v1/supplier-agreements", tags=["supplier-agreements"])


# ── LIST / SEARCH ──────────────────────────────────────────
@router.get("/", response_model=list[SupplierAgreementRead])
async def list_agreements(
    supplier_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all supplier agreements, optionally filtered by supplier_id."""
    stmt = select(SupplierAgreement)
    if supplier_id:
        stmt = stmt.where(SupplierAgreement.supplier_id == supplier_id)
    stmt = stmt.order_by(SupplierAgreement.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ── GET SINGLE ─────────────────────────────────────────────
@router.get("/{agreement_id}", response_model=SupplierAgreementRead)
async def get_agreement(agreement_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a single agreement by ID."""
    result = await db.execute(
        select(SupplierAgreement).where(SupplierAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return agreement


# ── UPLOAD & INDEX ─────────────────────────────────────────
@router.post("/upload", response_model=SupplierAgreementRead)
async def upload_agreement(
    file: UploadFile = File(...),
    supplier_id: str = Form(...),
    title: str | None = Form(None),
    valid_from: str | None = Form(None),
    valid_to: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF/text agreement file and create an index entry for RAG."""

    # Save file to a persistent location
    UPLOAD_DIR = "/home/admin/edm-v2/backend/uploads/agreements"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
    safe_name = f"{uuid4().hex}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create the database record
    agreement = SupplierAgreement(
        supplier_id=supplier_id,
        title=title or file.filename,
        file_path=file_path,
        valid_from=valid_from,
        valid_to=valid_to,
    )
    db.add(agreement)
    await db.commit()
    await db.refresh(agreement)

    return agreement


# ── RAG SEARCH ON AGREEMENT CONTENT ────────────────────────
@router.post("/search")
async def search_agreements(
    req: SupplierAgreementSearch,
    db: AsyncSession = Depends(get_db),
):
    """
    Full‑text search across supplier agreement titles and file names.

    This is a basic implementation that searches the agreement *title* and
    *file_path* fields. For a complete RAG pipeline, this should be
    extended to:
    - Extract text from the uploaded PDF/DOCX/TXT file.
    - Build a vector index (pgvector/FAISS) on the extracted content.
    - Use an LLM to generate enriched suggestions.
    """
    stmt = select(SupplierAgreement).where(
        or_(
            func.to_tsvector("english", SupplierAgreement.title).match(req.query),
            func.to_tsvector("english", SupplierAgreement.file_path).match(req.query),
        )
    )
    if req.supplier_id:
        stmt = stmt.where(SupplierAgreement.supplier_id == req.supplier_id)
    stmt = stmt.limit(req.limit)

    result = await db.execute(stmt)
    agreements = result.scalars().all()

    return {
        "query": req.query,
        "results": [a.to_dict() if hasattr(a, "to_dict") else {
            "id": str(a.id),
            "supplier_id": str(a.supplier_id),
            "title": a.title,
            "file_path": a.file_path,
        } for a in agreements],
    }


# ── DELETE ─────────────────────────────────────────────────
@router.delete("/{agreement_id}", status_code=204)
async def delete_agreement(agreement_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an agreement and its file."""
    result = await db.execute(
        select(SupplierAgreement).where(SupplierAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")

    # Remove the file from disk
    try:
        os.remove(agreement.file_path)
    except OSError:
        pass  # File may not exist

    await db.delete(agreement)
    await db.commit()