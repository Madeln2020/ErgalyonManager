# EDM v2 — Products Router (§6.1) — Multi-tenant with auth

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.models import Product, User, EnrichmentQueueItem
from app.schemas import ProductCreate, ProductList, ProductRead, ProductUpdate
from app.auth import get_current_user, require_role, Role
from app.services.cache import make_key, get_cached, set_cached, invalidate
from app.services.enrichment_service import process_enrichment
from app.services.audit_service import log_event

# Enrichment is now handled by the enrichment_service directly


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
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """List products scoped to the current user's organization."""
    cache_key = make_key(
        _CACHE_PREFIX,
        "list",
        search or "",
        str(supplier_id) if supplier_id else "none",
        str(category_k1_id) if category_k1_id else "none",
        limit,
        offset,
        str(current_user.organization_id),
    )
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    query = (
        select(Product)
        .where(Product.is_deleted == False)
        .where(Product.organization_id == current_user.organization_id)
    )

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

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    query = query.order_by(Product.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    data = ProductList(items=items, total=total)
    set_cached(cache_key, data.model_dump())
    return data


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False,
            Product.organization_id == current_user.organization_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Create a new product."""
    # Generate ergalyon_code: ERG-{seq:08d}
    # For simplicity, use a random 8-digit number; in production use a sequence.
    import random
    ergalyon_code = f"ERG-{random.randint(0, 99999999):08d}"
    # Build product data from schema + auto-generated fields
    product_data = data.model_dump()
    product_data["ergalyon_code"] = ergalyon_code
    product_data["organization_id"] = current_user.organization_id
    product_data["specs_json"] = product_data.get("specs_json") or {}
    product_data["description_normalized"] = product_data.get("description_normalized") or product_data["description"]
    product = Product(**product_data)
    db.add(product)
    await db.flush()
    await db.refresh(product)

    # Audit trail
    await log_event(
        entity_type="product",
        entity_id=product.id,
        event_name="created",
        payload=data.model_dump(),
        user_id=current_user.id,
        session=db,
    )

    # Invalidate caches
    invalidate(_CACHE_PREFIX, "list")
    return product


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False,
            Product.organization_id == current_user.organization_id,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    product.updated_by = current_user.id
    await db.flush()
    await db.refresh(product)

    invalidate(_CACHE_PREFIX, "list")
    invalidate(_CACHE_PREFIX, "detail", str(product_id))

    await log_event(
        entity_type="product",
        entity_id=product.id,
        event_name="updated",
        payload={"fields_updated": list(data.model_dump(exclude_unset=True).keys())},
        user_id=current_user.id,
        session=db,
    )

    return product


@router.post("/{product_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_product(
    product_id: UUID,
    background_tasks: BackgroundTasks,
    source: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(Role.USER)),
):
    """Trigger enrichment for a product (queues async job)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_deleted == False,
            Product.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    await log_event(
        entity_type="product",
        entity_id=product_id,
        event_name="enrichment_queued",
        payload={"source": source or "all"},
        user_id=current_user.id,
        session=db,
    )

    # Create enrichment queue item
    queue_item = EnrichmentQueueItem(
        product_id=product_id,
        enrichment_level="XML",  # Start with XML level; in reality, we would determine based on missing data
        source=source or "all",
        status="PENDING",
        priority=0,
    )
    db.add(queue_item)
    await db.flush()
    await db.refresh(queue_item)

    # Add background task to process the queue item
    background_tasks.add_task(process_enrichment, queue_item.id)

    return {
        "product_id": str(product_id),
        "job_id": f"enr_{product_id}_{queue_item.id}",
        "status": "queued",
        "queue_item_id": str(queue_item.id),
    }