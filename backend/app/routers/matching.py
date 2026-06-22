# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Matching Router (Match decisions, review queue)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MatchDecision
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/matching", tags=["Matching"])


class MatchDecisionRead(BaseModel):
    id: str
    parsed_line_item_id: str
    product_id: Optional[str]
    product_supplier_link_id: Optional[str]
    decision_type: str
    decided_at: Optional[str]


class MatchDecisionCreate(BaseModel):
    parsed_line_item_id: str
    product_id: Optional[str] = None
    product_supplier_link_id: Optional[str] = None
    decision_type: str
    candidates_json: Optional[dict] = None


class MatchTriggerRequest(BaseModel):
    parsed_document_id: str


class MatchTriggerResponse(BaseModel):
    items_matched: int
    parsed_document_id: str


@router.get("", response_model=list[MatchDecisionRead])
async def list_match_decisions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    decision_type: Optional[str] = None,
):
    """List all match decisions."""
    query = select(MatchDecision)
    if decision_type:
        query = query.where(MatchDecision.decision_type == decision_type)
    result = await db.execute(query)
    decisions = result.scalars().all()
    return [MatchDecisionRead(
        id=str(d.id),
        parsed_line_item_id=str(d.parsed_line_item_id),
        product_id=str(d.product_id) if d.product_id else None,
        product_supplier_link_id=str(d.product_supplier_link_id) if d.product_supplier_link_id else None,
        decision_type=d.decision_type,
        decided_at=str(d.decided_at) if d.decided_at else None,
    ) for d in decisions]


@router.post("/trigger", response_model=MatchTriggerResponse)
async def trigger_matching(
    data: MatchTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run product matching for all line items in a parsed document."""
    from uuid import UUID
    from app.services.matching_service import match_parsed_document

    parsed_doc_id = UUID(data.parsed_document_id)
    matched = await match_parsed_document(parsed_doc_id, current_user.company_id, db)

    return MatchTriggerResponse(
        items_matched=matched,
        parsed_document_id=data.parsed_document_id,
    )


@router.post("", response_model=MatchDecisionRead)
async def create_match_decision(
    data: MatchDecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("operator")),
):
    """Create a new match decision."""
    from uuid import UUID
    decision = MatchDecision(
        company_id=current_user.company_id,
        parsed_line_item_id=UUID(data.parsed_line_item_id),
        product_id=UUID(data.product_id) if data.product_id else None,
        product_supplier_link_id=UUID(data.product_supplier_link_id) if data.product_supplier_link_id else None,
        decision_type=data.decision_type,
        candidates_json=data.candidates_json,
        decided_by=current_user.id,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return MatchDecisionRead(
        id=str(decision.id),
        parsed_line_item_id=str(decision.parsed_line_item_id),
        product_id=str(decision.product_id) if decision.product_id else None,
        product_supplier_link_id=str(decision.product_supplier_link_id) if decision.product_supplier_link_id else None,
        decision_type=decision.decision_type,
        decided_at=str(decision.decided_at) if decision.decided_at else None,
    )
