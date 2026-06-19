# EDM v2 — Supplier Router (§6.1)  — Phase 4: Redis caching + Audit trail

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Supplier
from app.schemas import SupplierCreate, SupplierRead, SupplierUpdate
from app.services.cache import make_key, get_cached, set_cached, invalidate
from app.services.audit_service import log_event

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

_CACHE_PREFIX = "suppliers"


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)

    # Audit trail
    await log_event(
        entity_type="supplier",
        entity_id=supplier.id,
        event_name="created",
        payload=data.model_dump(),
        session=db,
    )

    # Invalidate list cache when a new supplier is added
    invalidate(_CACHE_PREFIX, "list")
    return supplier


@router.get("", response_model=list[SupplierRead])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    """List active suppliers with Redis cache (TTL 2 min)."""
    cache_key = make_key(_CACHE_PREFIX, "list")
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Supplier).where(Supplier.is_active == True))
    suppliers = result.scalars().all()
    data = [
        {
            "id": str(s.id),
            "name": s.name,
            "vat_number": s.vat_number,
            "country": s.country,
            "contact_email": s.contact_email,
            "contact_phone": s.contact_phone,
            "rules_json": s.rules_json,
            "parsing_profile": s.parsing_profile,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in suppliers
    ]
    set_cached(cache_key, data)
    return data


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get single supplier with Redis cache."""
    cache_key = make_key(_CACHE_PREFIX, "detail", str(supplier_id))
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: UUID, data: SupplierUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Snapshot old values for audit
    old_values = {field: getattr(supplier, field) for field in data.model_dump(exclude_unset=True)}

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    await db.flush()
    await db.refresh(supplier)

    # Audit trail
    await log_event(
        entity_type="supplier",
        entity_id=supplier.id,
        event_name="updated",
        payload={"old": {k: str(v) if v else None for k, v in old_values.items()},
                 "new": {k: str(v) if v else None for k, v in data.model_dump(exclude_unset=True).items()}},
        session=db,
    )

    # Invalidate both list and detail cache
    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(supplier_id))
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(supplier_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Soft delete: set inactive
    supplier.is_active = False
    await db.flush()

    # Audit trail
    await log_event(
        entity_type="supplier",
        entity_id=supplier_id,
        event_name="deleted",
        payload={"name": supplier.name, "vat_number": supplier.vat_number},
        session=db,
    )

    # Invalidate caches
    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(supplier_id))
