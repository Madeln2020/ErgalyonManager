# -*- coding: utf-8 -*-
"""EDM v2.1 — Review Service

Utility functions for creating review tasks.

The actual service logic for deciding when to create review tasks lives in
matching_service.py and enrichment_service.py; this module provides the
confirmation/creation helper.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import traceback

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import ReviewTask, MatchDecision


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def create_match_review_task(
    *,
    session: AsyncSession,
    company_id: UUID,
    md_id: UUID,
    candidate_json: Optional[dict] = None,
) -> Optional[ReviewTask]:
    """Create a match_confirm review task for an auto_suggested match.

    Only creates if the ``MatchDecision.decision_type`` is ``auto_suggested``;
    otherwise the matching engine has already resolved it (exact, manual,
    etc.).

    Returns the ``ReviewTask`` instance, or ``None`` if creation is skipped.
    """
    # Load the match decision to verify it's auto_suggested
    result = await session.execute(select(MatchDecision).where(MatchDecision.id == md_id))
    md = result.scalar_one_or_none()
    if not md:
        return None
    if md.decision_type != "auto_suggested":
        return None

    # Build entity_ref: "match_decisions:{md_id}"
    entity_ref = f"match_decisions:{md_id}"
    payload = {
        "match_decision_id": str(md_id),
        "parsed_line_item_id": str(md.parsed_line_item_id) if md.parsed_line_item_id else None,
        "candidate_product_id": str(md.product_id) if md.product_id else None,
        "candidate_supplier": str(md.product_supplier_link_id) if md.product_supplier_link_id else None,
        "candidate_json": candidate_json,
    }

    try:
        new_task = ReviewTask(
            company_id=company_id,
            task_type="match_confirm",
            entity_ref=entity_ref,
            status="open",
            priority="MEDIUM",  # Auto-suggested matches can be reviewed after other critical items
            payload_json=payload,
            created_at=_now_utc(),
            updated_at=_now_utc(),
        )
        session.add(new_task)
        await session.flush()
        await session.refresh(new_task)
        return new_task
    except Exception:
        # Log and swallow exceptions here; the matching pipeline can continue without a review task.
        traceback.print_exc()
        return None


async def mark_match_review_task_resolved(
    *,
    session: AsyncSession,
    task_id: UUID,
    resolved_by: UUID,
    resolution: str,
) -> "ReviewTask":
    """Mark a match_confirm review as resolved.

    If resolution is ``approved``, promote the underlying ``MatchDecision`` from
    ``auto_suggested`` to ``manual_confirm``.
    """
    # Load the task
    result = await session.execute(select(ReviewTask).where(ReviewTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError(f"Review task {task_id} not found")

    if task.task_type != "match_confirm":
        raise ValueError("Resolved task is not a match_confirm task")

    # Validate resolution
    if resolution not in {"approved", "rejected", "none"}:
        raise ValueError("Invalid resolution value")

    # Update the task first
    task.status = "done"
    task.resolution = resolution if resolution != "none" else None
    task.resolved_by = resolved_by
    task.resolved_at = _now_utc()
    task.closed_at = _now_utc()

    # If approved, promote the MatchDecision
    if resolution == "approved" and task.entity_ref:
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
        except Exception:
            # Log exception – not fatal to the overall process
            traceback.print_exc()

    await session.commit()
    await session.refresh(task)
    return task


async def create_enrichment_review_task(
    *,
    session: AsyncSession,
    company_id: UUID,
    product_id: UUID,
    source_ref: str,
    change_summary: Optional[dict] = None,
    priority: str = "MEDIUM",
) -> ReviewTask:
    """Create a match_confirm review task for an auto_suggested match.

    Only creates if the ``MatchDecision.decision_type`` is ``auto_suggested``;
    otherwise the matching engine has already resolved it (exact, manual,
    etc.).

    Returns the ``ReviewTask`` instance or ``None`` if creation is skipped.
    """
    try:
        entity_ref = f"products:{product_id}"
        payload = {
            "product_id": str(product_id),
            "source_ref": source_ref,
            "change_summary": change_summary,
        }
        new_task = ReviewTask(
            company_id=company_id,
            task_type="enrichment_confirm",
            entity_ref=entity_ref,
            status="open",
            priority=priority,
            payload_json=payload,
            created_at=_now_utc(),
            updated_at=_now_utc(),
        )
        session.add(new_task)
        await session.flush()
        await session.refresh(new_task)
        return new_task
    except Exception:
        traceback.print_exc()
        return None