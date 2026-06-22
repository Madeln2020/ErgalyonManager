# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Cost Management Router
# Handles cost updates, approval workflow, and cost history.
# ═══════════════════════════════════════════════════════════════════
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CostUpdate, ProductSupplierLink, Product
from app.routers.auth import get_current_user, require_role
from app.services.cost_service import (
    create_cost_update,
    approve_cost_update,
    reject_cost_update,
)

router = APIRouter(prefix="/api/v1/costs", tags=["Cost Management"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────
class CostUpdateRead(BaseModel):
    id: str
    product_id: str
    product_supplier_link_id: Optional[str]
    old_cost: Optional[float]
    new_cost: Optional[float]
    source: str
    source_ref: Optional[str]
    status: str
    approved_by: Optional[str]
    approved_at: Optional[str]
    created_at: Optional[str]


class CostUpdateCreate(BaseModel):
    product_id: str
    supplier_link_id: str
    new_cost: float
    source: str = "manual"
    source_ref: Optional[str] = None
    notes: Optional[str] = None


class CostUpdateAction(BaseModel):
    action: str  # "approve" or "reject"
    reason: Optional[str] = None


# ──────────────────────────────────────────
# GET / — List cost updates
# ──────────────────────────────────────────
@router.get("", response_model=List[CostUpdateRead])
async def list_cost_updates(
    company_id: UUID = Query(..., description="Company tenant ID"),
    status: Optional[str] = Query(None, description="Filter: pending|approved|rejected"),
    db: AsyncSession = Depends(get_db),
):
    """List cost updates for a company, optionally filtered by status."""
    stmt = select(CostUpdate).where(CostUpdate.company_id == company_id)
    if status:
        stmt = stmt.where(CostUpdate.status == status)
    result = await db.execute(stmt.order_by(CostUpdate.created_at.desc()))
    updates = result.scalars().all()
    return [
        CostUpdateRead(
            id=str(u.id),
            product_id=str(u.product_id),
            product_supplier_link_id=str(u.product_supplier_link_id) if u.product_supplier_link_id else None,
            old_cost=float(u.old_cost) if u.old_cost else None,
            new_cost=float(u.new_cost) if u.new_cost else None,
            source=u.source,
            source_ref=u.source_ref,
            status=u.status,
            approved_by=str(u.approved_by) if u.approved_by else None,
            approved_at=str(u.approved_at) if u.approved_at else None,
            created_at=str(u.created_at) if u.created_at else None,
        )
        for u in updates
    ]


# ──────────────────────────────────────────
# POST / — Create a manual cost update request
# ──────────────────────────────────────────
@router.post("", response_model=CostUpdateRead)
async def create_cost_update_endpoint(
    data: CostUpdateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manually create a pending cost update request.

    Cost protection: the new cost is NOT written to price_history until approved.
    """
    try:
        cost_update = await create_cost_update(
            db=db,
            company_id=current_user.company_id,
            product_id=UUID(data.product_id),
            supplier_link_id=UUID(data.supplier_link_id),
            new_cost=Decimal(str(data.new_cost)),
            source=data.source,
            source_ref=data.source_ref,
            notes=data.notes,
            user_id=current_user.id,
        )
        await db.commit()
        return CostUpdateRead(
            id=str(cost_update.id),
            product_id=str(cost_update.product_id),
            product_supplier_link_id=str(cost_update.product_supplier_link_id) if cost_update.product_supplier_link_id else None,
            old_cost=float(cost_update.old_cost) if cost_update.old_cost else None,
            new_cost=float(cost_update.new_cost) if cost_update.new_cost else None,
            source=cost_update.source,
            source_ref=cost_update.source_ref,
            status=cost_update.status,
            approved_by=str(cost_update.approved_by) if cost_update.approved_by else None,
            approved_at=str(cost_update.approved_at) if cost_update.approved_at else None,
            created_at=str(cost_update.created_at) if cost_update.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────
# PATCH /{cost_id} — Approve or reject a cost update
# ──────────────────────────────────────────
@router.patch("/{cost_id}", response_model=CostUpdateRead)
async def update_cost_status(
    cost_id: str,
    payload: CostUpdateAction,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("cost_approver")),
):
    """Approve or reject a pending cost update.

    - APPROVE: appends to price_history_json in ProductSupplierLink, updates current cost
    - REJECT: marks as rejected (no changes to price history)
    """
    from app.services.cost_service import approve_cost_update, reject_cost_update

    cost_uuid = UUID(cost_id)
    try:
        if payload.action == "approve":
            cost_update = await approve_cost_update(
                db=db,
                cost_update_id=cost_uuid,
                approved_by=current_user.id,
            )
        elif payload.action == "reject":
            cost_update = await reject_cost_update(
                db=db,
                cost_update_id=cost_uuid,
                rejected_by=current_user.id,
                reason=payload.reason,
            )
        else:
            raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

        await db.commit()
        return CostUpdateRead(
            id=str(cost_update.id),
            product_id=str(cost_update.product_id),
            product_supplier_link_id=str(cost_update.product_supplier_link_id) if cost_update.product_supplier_link_id else None,
            old_cost=float(cost_update.old_cost) if cost_update.old_cost else None,
            new_cost=float(cost_update.new_cost) if cost_update.new_cost else None,
            source=cost_update.source,
            source_ref=cost_update.source_ref,
            status=cost_update.status,
            approved_by=str(cost_update.approved_by) if cost_update.approved_by else None,
            approved_at=str(cost_update.approved_at) if cost_update.approved_at else None,
            created_at=str(cost_update.created_at) if cost_update.created_at else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ──────────────────────────────────────────
# GET /{cost_id}/history — Get price history for a supplier link
# ──────────────────────────────────────────
@router.get("/link/{supplier_link_id}/history")
async def get_price_history(
    supplier_link_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the price history for a supplier link (approved costs)."""
    result = await db.execute(
        select(ProductSupplierLink).where(ProductSupplierLink.id == UUID(supplier_link_id))
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Supplier link not found")

    history = []
    if link.price_history_json and isinstance(link.price_history_json, list):
        # Return only approved entries, sorted newest first
        approved = [e for e in link.price_history_json if e.get("status") == "approved"]
        history = sorted(approved, key=lambda x: x.get("approved_at", ""), reverse=True)

    return {
        "supplier_link_id": str(link.id),
        "product_id": str(link.product_id),
        "history": history,
    }