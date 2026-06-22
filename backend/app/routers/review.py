# -*- coding: utf-8 -*-
"""EDM v2.1 — Review Queue Router

Provides CRUD‑like endpoints for ``review_tasks`` so the frontend can list,
filter and resolve pending tasks (match confirmations, enrichment reviews,
etc.).
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import ReviewTask, MatchDecision
from app.schemas.review_schemas import (
    ReviewTaskOut,
    ReviewTaskDetailOut,
    ReviewResolveRequest,
)

router = APIRouter(prefix="/review", tags=["Review"])

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# List / filter tasks
# ---------------------------------------------------------------------------
@router.get("/tasks", response_model=List[ReviewTaskOut])
async def list_review_tasks(
    company_id: UUID = Query(..., description="Tenant company ID"),
    status: Optional[str] = Query(None, description="Filter by status (open|in_progress|done)"),
    task_type: Optional[str] = Query(None, description="Filter by task_type"),
    session: AsyncSession = Depends(get_db),
) -> List[ReviewTaskOut]:
    """Return all review tasks for a company, optionally filtered.

    Ordering: priority (ascending) then newest first.
    """
    stmt = select(ReviewTask).where(ReviewTask.company_id == company_id)
    if status:
        stmt = stmt.where(ReviewTask.status == status)
    if task_type:
        stmt = stmt.where(ReviewTask.task_type == task_type)
    stmt = stmt.order_by(ReviewTask.priority.asc(), ReviewTask.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

# ---------------------------------------------------------------------------
# Get a single task (full payload)
# ---------------------------------------------------------------------------
@router.get("/tasks/{task_id}", response_model=ReviewTaskDetailOut)
async def get_review_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> ReviewTaskDetailOut:
    result = await session.execute(
        select(ReviewTask)
        .where(ReviewTask.id == task_id)
        .options(joinedload(ReviewTask.company))
    )
    task = result.unique().scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
    return task

# ---------------------------------------------------------------------------
# Resolve / update a task
# ---------------------------------------------------------------------------
@router.patch("/tasks/{task_id}/resolve", response_model=ReviewTaskOut)
async def resolve_review_task(
    task_id: UUID,
    payload: ReviewResolveRequest,
    resolved_by: UUID = Query(..., description="User ID performing the resolve"),
    session: AsyncSession = Depends(get_db),
) -> ReviewTaskOut:
    """Mark a task as ``in_progress`` or ``done``.

    If the task is a ``match_confirm`` and the resolution is ``approved``,
    the underlying ``MatchDecision`` is promoted from ``auto_suggested``
    to ``manual_confirm``.
    """
    # Load the task
    result = await session.execute(select(ReviewTask).where(ReviewTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")

    if payload.status not in {"in_progress", "done"}:
        raise HTTPException(status_code=400, detail="Invalid status value")

    task.status = payload.status
    task.resolution = payload.resolution
    task.resolved_by = resolved_by
    task.resolved_at = _now_utc()
    if payload.status == "done":
        task.closed_at = _now_utc()

    # Special handling for match confirmations
    if (
        payload.status == "done"
        and payload.resolution == "approved"
        and task.task_type == "match_confirm"
        and task.entity_ref
    ):
        # entity_ref format: "match_decisions:{uuid}"
        try:
            table, pk = task.entity_ref.split(":")
            if table == "match_decisions":
                md_result = await session.execute(
                    select(MatchDecision).where(MatchDecision.id == UUID(pk))
                )
                md = md_result.scalar_one_or_none()
                if md and md.decision_type == "auto_suggested":
                    md.decision_type = "manual_confirm"
                    md.decided_by = resolved_by
                    md.decided_at = _now_utc()
                    await session.flush()
        except Exception:
            # Silently ignore malformed refs – they will be logged elsewhere.
            pass

    await session.commit()
    await session.refresh(task)
    return task

# ---------------------------------------------------------------------------
# Create a new review task (internal helper – not exposed publicly)
# ---------------------------------------------------------------------------
async def _create_review_task(
    *,
    session: AsyncSession,
    company_id: UUID,
    task_type: str,
    entity_ref: Optional[str] = None,
    priority: str = "MEDIUM",
    payload_json: Optional[dict] = None,
) -> ReviewTask:
    """Utility used by other services to insert a review task.

    Returns the persisted ``ReviewTask`` instance.
    """
    new_task = ReviewTask(
        company_id=company_id,
        task_type=task_type,
        entity_ref=entity_ref,
        status="open",
        priority=priority,
        payload_json=payload_json,
        created_at=_now_utc(),
        updated_at=_now_utc(),
    )
    session.add(new_task)
    await session.flush()
    await session.refresh(new_task)
    return new_task

# Note: the ``_create_review_task`` helper is intentionally *not* an API endpoint;
# it is imported by services (e.g., matching_service) where review is required.
