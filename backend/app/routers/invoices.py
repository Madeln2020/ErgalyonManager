# EDM v2 — Invoices Router (§6.1)

import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Invoice, InvoiceItem
from app.schemas import InvoiceItemRead, InvoiceRead
from app.services.pipeline import process_invoice_file

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])


@router.post("/upload", status_code=202)
async def upload_invoice(
    supplier_id: UUID = Form(...),
    document_type: str = Form("invoice"),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more invoice/offer files. Auto-processes them."""
    invoices = []
    for f in files:
        ext = f.filename.split(".")[-1].lower() if f.filename else "unknown"
        fmt = "pdf"
        if ext in ("xml",):
            fmt = "xml"
        elif ext in ("jpg", "jpeg", "png", "webp"):
            fmt = "image"
        elif ext in ("xlsx", "xls", "csv"):
            fmt = "excel"

        # Read file content into memory
        content = await f.read()

        invoice = Invoice(
            supplier_id=supplier_id,
            document_type=document_type,
            file_path=f"uploads/{f.filename}",
            file_format=fmt,
            status="uploaded",
        )
        db.add(invoice)
        await db.flush()
        await db.refresh(invoice)

        # Process through pipeline (sync for now; will move to Celery in Phase 2)
        try:
            await process_invoice_file(invoice, content, db)
        except Exception as e:
            invoice.status = "failed"
            invoice.error_message = str(e)
            await db.flush()

        invoices.append(invoice)

    return {
        "invoices": [InvoiceRead.model_validate(i).model_dump() for i in invoices],
        "job_id": f"job_{supplier_id}",
    }


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/{invoice_id}/items", response_model=list[InvoiceItemRead])
async def get_invoice_items(invoice_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InvoiceItem)
        .where(InvoiceItem.invoice_id == invoice_id)
        .order_by(InvoiceItem.line_number)
    )
    return result.scalars().all()
