# EDM v2.1 — Supplier Router (§6.1) — Multi-tenant with RBAC and AADE integration

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import SupplierCreate, SupplierRead, SupplierUpdate, SupplierListRead
from app.auth import get_current_user, require_role, Role
from app.services.supplier_service import (
    create_supplier,
    get_supplier,
    list_suppliers,
    update_supplier,
    delete_supplier,
)

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Create a new supplier. Requires USER+ role. Automatically fetches AADE profile if VAT provided."""
    supplier = await create_supplier(data, db, current_user)
    return supplier


@router.get("", response_model=list[SupplierListRead])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """List suppliers scoped to the user's company. Requires VIEWER+."""
    suppliers = await list_suppliers(db, current_user)
    return [SupplierListRead.model_validate(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """Get single supplier. Requires VIEWER+."""
    supplier = await get_supplier(supplier_id, db, current_user)
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
    """Update supplier. Requires ADMIN+ role. Automatically fetches AADE profile if VAT changes."""
    supplier = await update_supplier(supplier_id, data, db, current_user)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Soft-delete supplier. Requires ADMIN+ role."""
    supplier = await delete_supplier(supplier_id, db, current_user)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
