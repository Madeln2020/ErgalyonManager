# EDM v2 — Supplier Router (§6.1) — Multi-tenant with RBAC

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Supplier, User
from app.schemas import SupplierCreate, SupplierRead, SupplierUpdate, SupplierListRead
from app.auth import get_current_user, require_role, Role
from app.services.cache import make_key, get_cached, set_cached, invalidate
from app.services.audit_service import log_event

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

_CACHE_PREFIX = "suppliers"


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Create a new supplier. Requires USER role or above."""
    supplier = Supplier(**data.model_dump())
    supplier.organization_id = current_user.organization_id
    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)

    # Audit trail
    await log_event(
        entity_type="supplier",
        entity_id=supplier.id,
        event_name="created",
        payload=data.model_dump(),
        user_id=current_user.id,
        session=db,
    )

    invalidate(_CACHE_PREFIX, "list")
    return supplier


@router.get("", response_model=list[SupplierRead])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """List suppliers scoped to the user's organization. Requires VIEWER+."""
    cache_key = make_key(_CACHE_PREFIX, "list", str(current_user.organization_id))
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Supplier).where(
            Supplier.deleted_at.is_(None),
            Supplier.organization_id == current_user.organization_id,
        )
    )
    suppliers = result.scalars().all()
    set_cached(cache_key, suppliers)
    return suppliers


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """Get single supplier. Requires VIEWER+."""
    cache_key = make_key(_CACHE_PREFIX, "detail", str(supplier_id))
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Update supplier. Requires ADMIN or OWNER."""
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

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
        payload={
            "old": {k: str(v) if v else None for k, v in old_values.items()},
            "new": {k: str(v) if v else None for k, v in data.model_dump(exclude_unset=True).items()},
        },
        user_id=current_user.id,
        session=db,
    )

    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(supplier_id))
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Soft-delete supplier. Requires ADMIN or OWNER."""
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Soft delete
    supplier.deleted_at = datetime.now(timezone.utc)
    supplier.status = "INACTIVE"
    await db.flush()

    # Audit trail
    await log_event(
        entity_type="supplier",
        entity_id=supplier_id,
        event_name="deleted",
        payload={"name": supplier.name, "afm": supplier.afm},
        user_id=current_user.id,
        session=db,
    )

    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(supplier_id))
