# EDM v2 — Rule Tester Router (§8)
# Provides a dry-run endpoint to test rules against sample input.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.rule_engine import RuleEngine, NormalizedItem
from app.auth import require_role, Role
from app.models import User

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


class RuleTestRequest(BaseModel):
    rules_json: dict = {}
    sample_code: str = ""
    sample_description: str = ""


class RuleTestResponse(BaseModel):
    normalized_code: str
    normalized_description: str
    confidence: float
    rules_applied: list[dict]
    validation_errors: list[str]


@router.post("/test", response_model=RuleTestResponse)
async def test_rules(
    req: RuleTestRequest,
    current_user: User = Depends(require_role(Role.VIEWER)),
):
    """Dry-run: apply rules_json to sample input and return normalized result."""
    from decimal import Decimal

    engine = RuleEngine(req.rules_json, supplier_id="test")
    result = engine.normalize_item(
        raw_code=req.sample_code,
        raw_description=req.sample_description,
        quantity=Decimal("1"),
        unit_price=Decimal("0"),
        line_total=Decimal("0"),
    )

    return RuleTestResponse(
        normalized_code=result.normalized_supplier_code,
        normalized_description=result.normalized_description,
        confidence=result.confidence,
        rules_applied=[
            {
                "rule_type": r.rule_type,
                "field": r.field,
                "input": r.input_value,
                "output": r.output_value,
                "triggered": r.triggered,
            }
            for r in result.rules_applied
        ],
        validation_errors=result.validation_errors,
    )
