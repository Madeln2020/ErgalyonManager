# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Supplier Router (CRUD, AADE integration, contacts)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Supplier
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])


# ── Pydantic schemas ──────────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str
    vat_number: Optional[str] = None
    contacts_json: Optional[dict] = None
    default_currency: str = "EUR"
    default_parser: Optional[str] = None
    rules_json: Optional[dict] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None
    contacts_json: Optional[dict] = None
    default_currency: Optional[str] = None
    default_parser: Optional[str] = None
    rules_json: Optional[dict] = None
    is_active: Optional[bool] = None


class SupplierRead(BaseModel):
    id: str
    name: str
    vat_number: Optional[str]
    default_currency: str
    default_parser: Optional[str]
    is_active: bool
    created_at: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────
@router.get("", response_model=list[SupplierRead])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all active suppliers for the current user's company."""
    result = await db.execute(
        select(Supplier)
        .where(Supplier.is_active == True, Supplier.is_deleted == False)
    )
    suppliers = result.scalars().all()
    return [SupplierRead(
        id=str(s.id), name=s.name, vat_number=s.vat_number,
        default_currency=s.default_currency, default_parser=s.default_parser,
        is_active=s.is_active, created_at=str(s.created_at) if s.created_at else None
    ) for s in suppliers]


@router.post("", response_model=SupplierRead)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Create a new supplier."""
    supplier = Supplier(
        name=data.name,
        vat_number=data.vat_number,
        contacts_json=data.contacts_json,
        default_currency=data.default_currency,
        default_parser=data.default_parser,
        rules_json=data.rules_json,
        company_id=current_user.company_id,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return SupplierRead(
        id=str(supplier.id), name=supplier.name, vat_number=supplier.vat_number,
        default_currency=supplier.default_currency, default_parser=supplier.default_parser,
        is_active=supplier.is_active, created_at=str(supplier.created_at) if supplier.created_at else None
    )


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific supplier by ID."""
    from uuid import UUID
    result = await db.execute(
        select(Supplier).where(Supplier.id == UUID(supplier_id), Supplier.is_deleted == False)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return SupplierRead(
        id=str(supplier.id), name=supplier.name, vat_number=supplier.vat_number,
        default_currency=supplier.default_currency, default_parser=supplier.default_parser,
        is_active=supplier.is_active, created_at=str(supplier.created_at) if supplier.created_at else None
    )


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Update a supplier."""
    from uuid import UUID
    result = await db.execute(
        select(Supplier).where(Supplier.id == UUID(supplier_id))
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    await db.commit()
    await db.refresh(supplier)
    return SupplierRead(
        id=str(supplier.id), name=supplier.name, vat_number=supplier.vat_number,
        default_currency=supplier.default_currency, default_parser=supplier.default_parser,
        is_active=supplier.is_active, created_at=str(supplier.created_at) if supplier.created_at else None
    )
