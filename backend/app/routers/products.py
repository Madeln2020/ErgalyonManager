# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Product Router (CRUD, matching status, enrichment)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product, ProductSupplierLink
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


# ── Pydantic schemas ──────────────────────────────────────────────
class ProductCreate(BaseModel):
    canonical_name: str
    internal_code: Optional[str] = None
    technical_specs_json: Optional[dict] = None
    category_path: Optional[str] = None
    status: str = "active"


class ProductUpdate(BaseModel):
    canonical_name: Optional[str] = None
    internal_code: Optional[str] = None
    technical_specs_json: Optional[dict] = None
    category_path: Optional[str] = None
    status: Optional[str] = None


class ProductRead(BaseModel):
    id: str
    canonical_name: str
    internal_code: Optional[str]
    category_path: Optional[str]
    status: str
    created_at: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────
@router.get("", response_model=list[ProductRead])
async def list_products(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    status: Optional[str] = None,
):
    """List all products for the current company."""
    query = select(Product).where(Product.is_deleted == False)
    if status:
        query = query.where(Product.status == status)
    result = await db.execute(query)
    products = result.scalars().all()
    return [ProductRead(
        id=str(p.id), canonical_name=p.canonical_name,
        internal_code=p.internal_code, category_path=p.category_path,
        status=p.status, created_at=str(p.created_at) if p.created_at else None
    ) for p in products]


@router.post("", response_model=ProductRead)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Create a new product."""
    product = Product(
        canonical_name=data.canonical_name,
        internal_code=data.internal_code,
        technical_specs_json=data.technical_specs_json,
        category_path=data.category_path,
        status=data.status,
        company_id=current_user.company_id,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductRead(
        id=str(product.id), canonical_name=product.canonical_name,
        internal_code=product.internal_code, category_path=product.category_path,
        status=product.status, created_at=str(product.created_at) if product.created_at else None
    )


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific product by ID."""
    from uuid import UUID
    result = await db.execute(
        select(Product).where(Product.id == UUID(product_id), Product.is_deleted == False)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductRead(
        id=str(product.id), canonical_name=product.canonical_name,
        internal_code=product.internal_code, category_path=product.category_path,
        status=product.status, created_at=str(product.created_at) if product.created_at else None
    )
