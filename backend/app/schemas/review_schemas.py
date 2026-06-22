"""EDM v2.1 — Review Queue Schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewTaskOut(BaseModel):
    id: UUID
    company_id: UUID
    task_type: str
    entity_ref: Optional[str] = None
    status: str
    assigned_to: Optional[UUID] = None
    priority: str
    payload_json: Optional[dict] = None
    resolution: Optional[str] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewTaskDetailOut(ReviewTaskOut):
    """Extended detail — same fields for now, can add relationships later."""
    pass


class ReviewResolveRequest(BaseModel):
    status: str = Field(..., pattern=r"^(in_progress|done)$")
    resolution: Optional[str] = Field(None, description="approved | rejected | custom")
