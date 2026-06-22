# -*- coding: utf-8 -*-
"""EDM v2.1 — Cost Management Service

Handles creation, approval, and rejection of cost updates.
Implements cost protection: new costs create PENDING updates,
never overwrite existing cost data without explicit approval.

Workflow:
  1. Any source (enrichment, scraping, manual) discovers a new cost
     → creates CostUpdate with status="pending"
  2. Operator reviews pending costs
     → APPROVE: append to price_history_json, update current price
     → REJECT: keep as rejected (for audit)

Audit:
  - Every create, approve, reject action logs an audit record.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import CostUpdate, ProductSupplierLink, Product, AuditLog
from app.config import settings

logger = logging.getLogger("edm.cost")


def _now_utc():
    return datetime.now(timezone.utc)


async def create_cost_update(
    *,
    db: AsyncSession,
    company_id: UUID,
    product_id: UUID,
    supplier_link_id: UUID,
    new_cost: Decimal,
    source: str,
    source_ref: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[UUID] = None,
) -> CostUpdate:
    """Create a pending cost update request.

    The cost is NOT written to price_history_json until approved.
    This ensures cost protection as per spec.
    """
    # Normalize source to lowercase (constraint expects lowercase)
    source = source.lower()

    # Load supplier link to get current cost for old_cost
    link_result = await db.execute(
        select(ProductSupplierLink).where(ProductSupplierLink.id == supplier_link_id)
    )
    link = link_result.scalar_one_or_none()
    old_cost = None
    if link and link.price_history_json:
        # Try to get the latest approved cost from history
        history = link.price_history_json if isinstance(link.price_history_json, list) else []
        approved_costs = [e for e in history if e.get("status") == "approved"]
        if approved_costs:
            # Most recent approved cost
            latest = sorted(approved_costs, key=lambda x: x.get("approved_at", ""), reverse=True)[0]
            old_cost = Decimal(str(latest.get("cost", 0)))

    cost_update = CostUpdate(
        company_id=company_id,
        product_id=product_id,
        product_supplier_link_id=supplier_link_id,
        old_cost=old_cost,
        new_cost=new_cost,
        source=source,
        source_ref=source_ref,
        status="pending",
    )
    db.add(cost_update)
    await db.flush()
    await db.refresh(cost_update)

    # Audit log: create
    audit = AuditLog(
        company_id=company_id,
        entity_type="CostUpdate",
        entity_id=cost_update.id,
        action="create",
        payload_json={
            "source": source,
            "new_cost": float(new_cost) if new_cost else None,
            "old_cost": float(old_cost) if old_cost else None,
            "notes": notes,
        },
        user_id=user_id,
    )
    db.add(audit)

    logger.info(
        f"Created pending cost update for product {product_id}: "
        f"{old_cost} → {new_cost} (source={source})"
    )
    return cost_update


async def approve_cost_update(
    *,
    db: AsyncSession,
    cost_update_id: UUID,
    approved_by: Optional[UUID],
) -> CostUpdate:
    """Approve a pending cost update.

    When approved:
    1. Update CostUpdate status to "approved"
    2. Append the cost to ProductSupplierLink.price_history_json
    3. Set the current cost in the JSON (latest_approved_cost field)
    """
    result = await db.execute(
        select(CostUpdate).where(CostUpdate.id == cost_update_id)
    )
    cost_update = result.scalar_one_or_none()
    if not cost_update:
        raise ValueError(f"Cost update {cost_update_id} not found")

    if cost_update.status != "pending":
        raise ValueError(f"Cost update is already {cost_update.status}")

    # Load the supplier link
    link_result = await db.execute(
        select(ProductSupplierLink).where(ProductSupplierLink.id == cost_update.product_supplier_link_id)
    )
    link = link_result.scalar_one_or_none()
    if not link:
        raise ValueError(f"ProductSupplierLink {cost_update.product_supplier_link_id} not found")

    # Build history entry
    history_entry = {
        "cost": float(cost_update.new_cost),
        "source": cost_update.source,
        "source_ref": cost_update.source_ref,
        "approved_at": _now_utc().isoformat(),
        "approved_by": str(approved_by),
        "cost_update_id": str(cost_update.id),
        "status": "approved",
    }

    # Update price_history_json
    history = []
    if link.price_history_json and isinstance(link.price_history_json, list):
        history = link.price_history_json
    history.append(history_entry)
    link.price_history_json = history

    # Update cost_update status
    cost_update.status = "approved"
    cost_update.approved_by = approved_by
    cost_update.approved_at = _now_utc()

    # Audit log: approve
    audit = AuditLog(
        company_id=cost_update.company_id,
        entity_type="CostUpdate",
        entity_id=cost_update.id,
        action="update",
        payload_json={
            "new_cost": float(cost_update.new_cost) if cost_update.new_cost else None,
            "approved_by": str(approved_by),
        },
        user_id=approved_by,
    )
    db.add(audit)

    await db.flush()
    logger.info(
        f"Approved cost update {cost_update_id}: "
        f"new cost {cost_update.new_cost} appended to price_history_json for link {link.id}"
    )

    # Fire webhook if enabled
    if settings.COST_APPROVAL_WEBHOOK_ENABLED:
        asyncio.create_task(_send_webhook("cost_approved", {
            "cost_update_id": str(cost_update.id),
            "product_id": str(cost_update.product_id),
            "new_cost": float(cost_update.new_cost) if cost_update.new_cost else None,
            "old_cost": float(cost_update.old_cost) if cost_update.old_cost else None,
            "source": cost_update.source,
            "approved_by": str(approved_by),
            "approved_at": _now_utc().isoformat(),
        }))

    return cost_update


async def reject_cost_update(
    *,
    db: AsyncSession,
    cost_update_id: UUID,
    rejected_by: Optional[UUID] = None,
    reason: Optional[str] = None,
) -> CostUpdate:
    """Reject a pending cost update.

    Only marks as rejected; does NOT modify price_history.json.
    """
    result = await db.execute(
        select(CostUpdate).where(CostUpdate.id == cost_update_id)
    )
    cost_update = result.scalar_one_or_none()
    if not cost_update:
        raise ValueError(f"Cost update {cost_update_id} not found")

    if cost_update.status != "pending":
        raise ValueError(f"Cost update is already {cost_update.status}")

    cost_update.status = "rejected"
    cost_update.rejected_by = rejected_by
    cost_update.rejected_at = _now_utc()

    # Audit log: reject
    audit = AuditLog(
        company_id=cost_update.company_id,
        entity_type="CostUpdate",
        entity_id=cost_update.id,
        action="update",
        payload_json={
            "reason": reason,
            "rejected_by": str(rejected_by) if rejected_by else None,
        },
        user_id=rejected_by,
    )
    db.add(audit)

    await db.flush()
    logger.info(f"Rejected cost update {cost_update_id}" + (f" reason: {reason}" if reason else ""))

    # Fire webhook if enabled
    if settings.COST_APPROVAL_WEBHOOK_ENABLED:
        asyncio.create_task(_send_webhook("cost_rejected", {
            "cost_update_id": str(cost_update.id),
            "product_id": str(cost_update.product_id),
            "new_cost": float(cost_update.new_cost) if cost_update.new_cost else None,
            "old_cost": float(cost_update.old_cost) if cost_update.old_cost else None,
            "source": cost_update.source,
            "reason": reason,
            "rejected_at": _now_utc().isoformat(),
        }))

    return cost_update


# ── Webhook helper ──────────────────────────────────────────────────────

async def _send_webhook(event_type: str, payload: dict) -> None:
    """Fire a webhook notification for cost approval/rejection events.

    Uses httpx to POST to the configured webhook URL.
    Fire-and-forget pattern — failures are logged but never raised.
    """
    url = settings.COST_APPROVAL_WEBHOOK_URL
    if not url:
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={
                    "event": event_type,
                    "timestamp": _now_utc().isoformat(),
                    **payload,
                },
            )
            logger.info(
                "Webhook %s sent to %s: status=%d",
                event_type, url, response.status_code,
            )
    except ImportError:
        logger.warning("httpx not installed — webhook skipped")
    except Exception as exc:
        logger.warning("Webhook %s failed: %s", event_type, exc)