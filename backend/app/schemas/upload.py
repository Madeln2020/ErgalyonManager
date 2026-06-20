"""
EDM v2.1 — Upload Schemas
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    """Request body for file upload."""
    supplier_id: UUID = Field(..., description="Supplier to associate with this upload")
    file: bytes = Field(..., description="File content as bytes")


class UploadResponse(BaseModel):
    """Response for successful upload."""
    id: UUID
    company_id: UUID
    supplier_id: Optional[UUID]
    file_type: str
    object_key: str
    sha256: str
    original_filename: Optional[str]
    uploaded_by: Optional[UUID]
    uploaded_at: datetime
    parse_status: str = "pending"
    message: str = "File uploaded successfully and parsing started"


class UploadBatchRequest(BaseModel):
    """Request body for batch file upload."""
    supplier_id: UUID = Field(..., description="Supplier to associate with these uploads")


class UploadBatchResponse(BaseModel):
    """Response for batch upload."""
    uploaded_files: list[UploadResponse]
    total_count: int
    success_count: int
    failed_count: int
    errors: list[dict] = []


class ParseStatusResponse(BaseModel):
    """Response with parsing status."""
    id: UUID
    inbound_file_id: UUID
    doc_kind: str
    parse_status: str
    parser_version: Optional[str]
    confidence_score: Optional[Decimal]
    header_json: Optional[dict]
    line_item_count: int
    created_at: datetime
    updated_at: datetime


class ParseLineItemRead(BaseModel):
    """Single parsed line item."""
    id: UUID
    company_id: UUID
    parsed_document_id: UUID
    line_index: int
    supplier_sku_raw: Optional[str]
    supplier_sku_normalized: Optional[str]
    description_raw: Optional[str]
    description_normalized: Optional[str]
    qty: Optional[Decimal]
    unit_price: Optional[Decimal]
    line_total: Optional[Decimal]
    vat_rate: Optional[Decimal]
    extraction_source: str
    extraction_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
