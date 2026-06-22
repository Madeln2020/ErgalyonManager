# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Invoices Router (Parsed documents view, status)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ParsedDocument, ParsedLineItem
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


class ParsedDocRead(BaseModel):
    id: str
    doc_kind: str
    parse_status: str
    confidence_score: Optional[float]
    created_at: Optional[str]


class ParsedLineItemRead(BaseModel):
    id: str
    line_index: int
    supplier_sku_raw: Optional[str]
    supplier_sku_normalized: Optional[str]
    description_raw: Optional[str]
    qty: Optional[float]
    unit_price: Optional[float]
    line_total: Optional[float]
    vat_rate: Optional[float]
    extraction_source: str


@router.get("", response_model=list[ParsedDocRead])
async def list_parsed_documents(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    parse_status: Optional[str] = None,
):
    """List all parsed documents for the company."""
    query = select(ParsedDocument)
    if parse_status:
        query = query.where(ParsedDocument.parse_status == parse_status)
    result = await db.execute(query)
    docs = result.scalars().all()
    return [ParsedDocRead(
        id=str(d.id), doc_kind=d.doc_kind, parse_status=d.parse_status,
        confidence_score=float(d.confidence_score) if d.confidence_score else None,
        created_at=str(d.created_at) if d.created_at else None
    ) for d in docs]


@router.get("/{doc_id}", response_model=ParsedDocRead)
async def get_parsed_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific parsed document."""
    from uuid import UUID
    result = await db.execute(
        select(ParsedDocument).where(ParsedDocument.id == UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return ParsedDocRead(
        id=str(doc.id), doc_kind=doc.doc_kind, parse_status=doc.parse_status,
        confidence_score=float(doc.confidence_score) if doc.confidence_score else None,
        created_at=str(doc.created_at) if doc.created_at else None
    )


@router.get("/{doc_id}/items", response_model=list[ParsedLineItemRead])
async def get_parsed_line_items(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get all line items for a parsed document."""
    from uuid import UUID
    result = await db.execute(
        select(ParsedLineItem)
        .where(ParsedLineItem.parsed_document_id == UUID(doc_id))
        .order_by(ParsedLineItem.line_index)
    )
    items = result.scalars().all()
    return [ParsedLineItemRead(
        id=str(i.id), line_index=i.line_index,
        supplier_sku_raw=i.supplier_sku_raw,
        supplier_sku_normalized=i.supplier_sku_normalized,
        description_raw=i.description_raw,
        qty=float(i.qty) if i.qty else None,
        unit_price=float(i.unit_price) if i.unit_price else None,
        line_total=float(i.line_total) if i.line_total else None,
        vat_rate=float(i.vat_rate) if i.vat_rate else None,
        extraction_source=i.extraction_source,
    ) for i in items]
