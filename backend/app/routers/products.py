# EDM v2 — Products Router (§6.1)  — Phase 4: Redis caching

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductList, ProductRead, ProductUpdate
from app.services.cache import make_key, get_cached, set_cached, invalidate
from app.services.audit_service import log_event

router = APIRouter(prefix="/api/v1/products", tags=["products"])

_CACHE_PREFIX = "products"


@router.get("", response_model=ProductList)
async def list_products(
    search: str = Query(None),
    supplier_id: UUID = Query(None),
    category_k1_id: UUID = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List products with Redis cache for the exact query parameters."""
    # Build a deterministic cache key from query params
    cache_key = make_key(
        _CACHE_PREFIX,
        "list",
        search or "",
        str(supplier_id) if supplier_id else "none",
        str(category_k1_id) if category_k1_id else "none",
        limit,
        offset,
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    query = select(Product).where(Product.is_deleted == False)

    if search:
        query = query.where(
            Product.description_normalized.ilike(f"%{search}%")
            | Product.supplier_code.ilike(f"%{search}%")
            | Product.ergalyon_code.ilike(f"%{search}%")
        )
    if supplier_id:
        query = query.where(Product.supplier_id == supplier_id)
    if category_k1_id:
        query = query.where(Product.category_k1_id == category_k1_id)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    # Paginated results
    query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    data = ProductList(items=items, total=total)
    set_cached(cache_key, data.dict())
    return data


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)
    # Invalidate list and detail caches
    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(product_id))

    # Audit trail
    await log_event(
        entity_type="product",
        entity_id=product.id,
        event_name="updated",
        payload={"fields_updated": list(data.model_dump(exclude_unset=True).keys())},
        session=db,
    )

    return product


@router.post("/{product_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_product(product_id: UUID, source: str = Query(None), db: AsyncSession = Depends(get_db)):
    """Trigger enrichment for a product (queues async job)."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    # Audit trail
    await log_event(
        entity_type="product",
        entity_id=product_id,
        event_name="enrichment_queued",
        payload={"source": source or "all"},
        session=db,
    )

    # TODO: Implement actual enrichment job dispatch based on source
    # For now, just acknowledge
    return {
        "product_id": str(product_id),
        "job_id": f"enr_{product_id}_{source or 'all'}",
        "status": "queued",
    }
