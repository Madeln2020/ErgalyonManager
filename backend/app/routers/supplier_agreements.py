"""
EDM v2 – Supplier Agreement Router
Handles document upload, full‑text indexing, and RAG search on supplier agreements.
Multi-tenant with auth.
"""

import os
from uuid import uuid4, UUID
from datetime import date
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SupplierAgreement, User
from app.schemas import (
    SupplierAgreementCreate,
    SupplierAgreementRead,
    SupplierAgreementSearch,
)
from app.auth import get_current_user, require_role, Role

router = APIRouter(prefix="/api/v1/supplier-agreements", tags=["supplier-agreements"])


# ── LIST / SEARCH ──────────────────────────────────────────
@router.get("/", response_model=list[SupplierAgreementRead])
async def list_agreements(
    supplier_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List supplier agreements scoped to the current organization."""
    stmt = select(SupplierAgreement).where(
        SupplierAgreement.organization_id == current_user.organization_id
    )
    if supplier_id:
        stmt = stmt.where(SupplierAgreement.supplier_id == supplier_id)
    stmt = stmt.order_by(SupplierAgreement.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ── GET SINGLE ─────────────────────────────────────────────
@router.get("/{agreement_id}", response_model=SupplierAgreementRead)
async def get_agreement(
    agreement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single agreement by ID."""
    result = await db.execute(
        select(SupplierAgreement).where(
            SupplierAgreement.id == agreement_id,
            SupplierAgreement.organization_id == current_user.organization_id,
        )
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return agreement


# ── UPLOAD & INDEX ─────────────────────────────────────────
@router.post("/upload", response_model=SupplierAgreementRead)
async def upload_agreement(
    file: UploadFile = File(...),
    supplier_id: UUID = Form(...),
    title: str | None = Form(None),
    valid_from: date | None = Form(None),
    valid_to: date | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF/text agreement file."""
    UPLOAD_DIR = "/home/admin/edm-v2/backend/uploads/agreements"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_ext = file.filename.split(".")[-1] if file.filename else "pdf"
    safe_name = f"{uuid4().hex}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    agreement = SupplierAgreement(
        supplier_id=supplier_id,
        organization_id=current_user.organization_id,
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
    current_user: User = Depends(get_current_user),
):
    """Full‑text search across supplier agreement titles."""
    stmt = select(SupplierAgreement).where(
        SupplierAgreement.organization_id == current_user.organization_id,
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
        "results": [{
            "id": str(a.id),
            "supplier_id": str(a.supplier_id),
            "title": a.title,
            "file_path": a.file_path,
        } for a in agreements],
    }


# ── DELETE ─────────────────────────────────────────────────
@router.delete("/{agreement_id}", status_code=204)
async def delete_agreement(
    agreement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an agreement and its file."""
    result = await db.execute(
        select(SupplierAgreement).where(
            SupplierAgreement.id == agreement_id,
            SupplierAgreement.organization_id == current_user.organization_id,
        )
    )
    agreement = result.scalar_one_or_none()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")

    try:
        os.remove(agreement.file_path)
    except OSError:
        pass

    await db.delete(agreement)
    await db.commit()
