# EDM v2 — Export Router (§6.1)

import csv
import io
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Product

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("")
async def export_products(
    format: str = Query("csv", pattern="^(csv|excel|json|xml)$"),
    supplier_id: UUID = Query(None),
    category_k1_id: UUID = Query(None),
    date_from: date = Query(None),
    date_to: date = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(Product.is_deleted == False)

    if supplier_id:
        query = query.where(Product.supplier_id == supplier_id)
    if category_k1_id:
        query = query.where(Product.category_k1_id == category_k1_id)

    result = await db.execute(query)
    products = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ergalyon_code", "supplier_code", "manufacturer_code",
            "ean", "description", "current_price", "currency",
        ])
        for p in products:
            writer.writerow([
                p.ergalyon_code, p.supplier_code, p.manufacturer_code,
                p.ean, p.description, p.current_price, p.price_currency,
            ])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=edm_export.csv"},
        )

    elif format == "json":
        items = []
        for p in products:
            items.append({
                "ergalyon_code": p.ergalyon_code,
                "supplier_code": p.supplier_code,
                "manufacturer_code": p.manufacturer_code,
                "ean": p.ean,
                "description": p.description,
                "current_price": float(p.current_price) if p.current_price else None,
                "currency": p.price_currency,
            })
        return {"total": len(items), "items": items}

    else:
        raise HTTPException(status_code=400, detail=f"Format '{format}' not yet implemented")
