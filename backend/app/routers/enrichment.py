# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Enrichment Router (Trigger, events, manual edits)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EnrichmentEvent, Product, EnrichmentQueueItem
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/enrichment", tags=["Enrichment"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────
class EnrichmentEventRead(BaseModel):
    id: str
    product_id: str
    source_type: str
    source_ref: Optional[str]
    changes_json: Optional[dict]
    applied_at: Optional[str]
    created_at: Optional[str]


class EnrichmentTriggerRequest(BaseModel):
    product_id: str
    source: str = "all"  # xml, catalog, product_list, manual, web_scraping, all
    enrichment_level: Optional[str] = None  # XML, CATALOG, PRODUCT_LIST, MANUAL, WEB_SCRAPING, None=all


class EnrichmentTriggerResponse(BaseModel):
    id: str
    product_id: str
    status: str
    message: str


class EnrichmentManualEdit(BaseModel):
    """Manual product edit via enrichment."""
    product_id: str
    canonical_name: Optional[str] = None
    internal_code: Optional[str] = None
    technical_specs_json: Optional[dict] = None
    category_path: Optional[str] = None
    notes: Optional[str] = None


# ──────────────────────────────────────────
# GET — List enrichment events
# ──────────────────────────────────────────
@router.get("", response_model=list[EnrichmentEventRead])
async def list_enrichment_events(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    source_type: Optional[str] = None,
    product_id: Optional[str] = None,
):
    """List enrichment events."""
    query = select(EnrichmentEvent)
    if source_type:
        query = query.where(EnrichmentEvent.source_type == source_type)
    if product_id:
        from uuid import UUID
        query = query.where(EnrichmentEvent.product_id == UUID(product_id))
    result = await db.execute(query.order_by(EnrichmentEvent.created_at.desc()))
    events = result.scalars().all()
    return [EnrichmentEventRead(
        id=str(e.id), product_id=str(e.product_id),
        source_type=e.source_type, source_ref=e.source_ref,
        changes_json=e.changes_json,
        applied_at=str(e.applied_at) if e.applied_at else None,
        created_at=str(e.created_at) if e.created_at else None,
    ) for e in events]


# ──────────────────────────────────────────
# GET — Product enrichment history
# ──────────────────────────────────────────
@router.get("/product/{product_id}", response_model=list[EnrichmentEventRead])
async def get_product_enrichment_history(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get enrichment history for a product."""
    from uuid import UUID
    result = await db.execute(
        select(EnrichmentEvent)
        .where(EnrichmentEvent.product_id == UUID(product_id))
        .order_by(EnrichmentEvent.created_at.desc())
    )
    events = result.scalars().all()
    return [EnrichmentEventRead(
        id=str(e.id), product_id=str(e.product_id),
        source_type=e.source_type, source_ref=e.source_ref,
        changes_json=e.changes_json,
        applied_at=str(e.applied_at) if e.applied_at else None,
        created_at=str(e.created_at) if e.created_at else None,
    ) for e in events]


# ──────────────────────────────────────────
# POST — Trigger enrichment for a product
# ──────────────────────────────────────────
@router.post("/trigger", response_model=EnrichmentTriggerResponse)
async def trigger_enrichment(
    data: EnrichmentTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create an enrichment queue item and trigger processing in background."""
    from uuid import UUID

    # Verify product exists and belongs to user's company
    product_result = await db.execute(
        select(Product).where(
            Product.id == UUID(data.product_id),
            Product.company_id == current_user.company_id,
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate source
    valid_sources = {"xml", "catalog", "product_list", "manual", "web_scraping", "all"}
    if data.source.lower() not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {data.source}. Must be one of: {valid_sources}"
        )

    # Validate enrichment_level if provided
    if data.enrichment_level:
        valid_levels = {"XML", "CATALOG", "PRODUCT_LIST", "MANUAL", "WEB_SCRAPING"}
        if data.enrichment_level.upper() not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid enrichment_level: {data.enrichment_level}. Must be one of: {valid_levels}"
            )

    # Check if there's already a PENDING enrichment for this product
    existing = await db.execute(
        select(EnrichmentQueueItem).where(
            EnrichmentQueueItem.product_id == product.id,
            EnrichmentQueueItem.status == "PENDING",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="A PENDING enrichment already exists for this product"
        )

    # Create queue item
    queue_item = EnrichmentQueueItem(
        company_id=current_user.company_id,
        product_id=product.id,
        source=data.source.lower(),
        enrichment_level=data.enrichment_level.upper() if data.enrichment_level else None,
        status="PENDING",
    )
    db.add(queue_item)
    await db.commit()
    await db.refresh(queue_item)

    # Schedule background processing
    background_tasks.add_task(
        _run_enrichment_background,
        str(queue_item.id),
    )

    return EnrichmentTriggerResponse(
        id=str(queue_item.id),
        product_id=str(product.id),
        status="PENDING",
        message=f"Enrichment queued (source={data.source}, level={data.enrichment_level or 'all'})",
    )


# ──────────────────────────────────────────
# POST — Manual edit (Level 4 enrichment shortcut)
# ──────────────────────────────────────────
@router.post("/manual-edit", response_model=EnrichmentTriggerResponse)
async def manual_edit_product(
    data: EnrichmentManualEdit,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
):
    """Manually edit a product's data and record it as an enrichment event."""
    from uuid import UUID
    from datetime import datetime, timezone

    # Find product
    product_result = await db.execute(
        select(Product).where(
            Product.id == UUID(data.product_id),
            Product.company_id == current_user.company_id,
        )
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Track changes
    changes = {}
    if data.canonical_name and data.canonical_name != product.canonical_name:
        changes["canonical_name"] = {"old": product.canonical_name, "new": data.canonical_name}
        product.canonical_name = data.canonical_name
    if data.internal_code and data.internal_code != product.internal_code:
        changes["internal_code"] = {"old": product.internal_code, "new": data.internal_code}
        product.internal_code = data.internal_code
    if data.technical_specs_json and data.technical_specs_json != product.technical_specs_json:
        changes["technical_specs_json"] = {"old": product.technical_specs_json, "new": data.technical_specs_json}
        product.technical_specs_json = data.technical_specs_json
    if data.category_path and data.category_path != product.category_path:
        changes["category_path"] = {"old": product.category_path, "new": data.category_path}
        product.category_path = data.category_path

    if not changes:
        return EnrichmentTriggerResponse(
            id="",
            product_id=str(product.id),
            status="SKIPPED",
            message="No changes detected",
        )

    # If product was provisional, upgrade to active
    if product.status == "provisional":
        changes["status"] = {"old": "provisional", "new": "active"}
        product.status = "active"

    # Record enrichment event
    event = EnrichmentEvent(
        company_id=current_user.company_id,
        product_id=product.id,
        source_type="manual",
        source_ref=data.notes,
        changes_json=changes,
        applied_by=current_user.id,
        applied_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()

    return EnrichmentTriggerResponse(
        id=str(event.id),
        product_id=str(product.id),
        status="COMPLETED",
        message=f"Manual edit applied: {list(changes.keys())}",
    )


# ──────────────────────────────────────────
# Background enrichment runner
# ──────────────────────────────────────────
async def _run_enrichment_background(queue_item_id: str):
    """Run enrichment in a background task."""
    from uuid import UUID
    from app.services.enrichment_service import process_enrichment
    await process_enrichment(UUID(queue_item_id))
