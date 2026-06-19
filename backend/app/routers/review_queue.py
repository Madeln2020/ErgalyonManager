# EDM v2 — Review Queue Router (§6.1, §7)

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ReviewQueueItem
from app.schemas import ReviewQueueList, ReviewQueueRead, ReviewResolve

router = APIRouter(prefix="/api/v1/review-queue", tags=["review"])


@router.get("", response_model=ReviewQueueList)
async def list_review_queue(
    status: str = Query("open"),
    priority: str = Query(None),
    review_type: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(ReviewQueueItem)

    if status:
        query = query.where(ReviewQueueItem.status == status)
    if priority:
        query = query.where(ReviewQueueItem.priority == priority)
    if review_type:
        query = query.where(ReviewQueueItem.review_type == review_type)

    # Total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    # Sorted by priority (CRITICAL first) then oldest first
    priority_order = func.array_position(
        ["CRITICAL", "HIGH", "MEDIUM", "LOW"], ReviewQueueItem.priority
    )
    query = (
        query.order_by(priority_order, ReviewQueueItem.created_at)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return ReviewQueueList(total=total, items=items)


@router.post("/{review_id}/resolve")
async def resolve_review_item(
    review_id: UUID,
    resolution: ReviewResolve,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReviewQueueItem).where(ReviewQueueItem.id == review_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    item.status = "resolved"
    item.resolution = resolution.resolution

    await db.flush()
    await db.refresh(item)
    return {
        "id": str(item.id),
        "status": item.status,
        "resolution": item.resolution,
        "resolved_at": str(item.resolved_at) if item.resolved_at else None,
    }
