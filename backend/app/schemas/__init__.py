# ═══════════════════════════════════════════════════════════════════════
# EDM v2.1 — Pydantic Schemas (aligned with 15-table data model)
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# 1. Company
# ──────────────────────────────────────────
class CompanyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    vat_number: Optional[str] = Field(None, max_length=20)
    settings_json: Optional[dict] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None
    settings_json: Optional[dict] = None


class CompanyRead(BaseModel):
    id: UUID
    name: str
    vat_number: Optional[str]
    settings_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 2. User
# ──────────────────────────────────────────
class UserCreate(BaseModel):
    company_id: UUID
    email: str = Field(..., max_length=255)
    password_hash: str = Field(..., max_length=255)
    role: str = Field(..., pattern=r"^(viewer|user|admin|owner)$")
    display_name: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class UserRead(BaseModel):
    id: UUID
    company_id: UUID
    email: str
    role: str
    display_name: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None


# ──────────────────────────────────────────
# 3. Supplier
# ──────────────────────────────────────────
class SupplierCreate(BaseModel):
    company_id: UUID
    name: str = Field(..., max_length=255)
    vat_number: Optional[str] = Field(None, max_length=20)
    tax_profile_json: Optional[dict] = None
    contacts_json: Optional[dict] = None
    default_currency: str = "EUR"
    default_parser: Optional[str] = Field(None, max_length=50)
    rules_json: Optional[dict] = None
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None
    tax_profile_json: Optional[dict] = None
    contacts_json: Optional[dict] = None
    default_currency: Optional[str] = None
    default_parser: Optional[str] = None
    rules_json: Optional[dict] = None
    is_active: Optional[bool] = None


class SupplierRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    vat_number: Optional[str]
    tax_profile_json: Optional[dict]
    contacts_json: Optional[dict]
    default_currency: str
    default_parser: Optional[str]
    rules_json: Optional[dict]
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierListRead(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    vat_number: Optional[str]
    default_currency: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 4. SupplierDocument
# ──────────────────────────────────────────
class SupplierDocumentCreate(BaseModel):
    supplier_id: UUID
    company_id: UUID
    doc_type: str = Field(..., pattern=r"^(agreement|catalog|price_list|other)$")
    object_key: str
    title: Optional[str] = Field(None, max_length=255)
    extracted_text_object_key: Optional[str] = None
    embedding_ref: Optional[str] = None


class SupplierDocumentRead(BaseModel):
    id: UUID
    supplier_id: UUID
    company_id: UUID
    doc_type: str
    object_key: str
    title: Optional[str]
    extracted_text_object_key: Optional[str]
    embedding_ref: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 5. InboundFile
# ──────────────────────────────────────────
class InboundFileCreate(BaseModel):
    company_id: UUID
    supplier_id: Optional[UUID] = None
    file_type: str = Field(..., pattern=r"^(pdf|xml|xlsx|img)$")
    object_key: str
    sha256: str = Field(..., min_length=64, max_length=64)
    original_filename: Optional[str] = Field(None, max_length=500)
    uploaded_by: Optional[UUID] = None


class InboundFileRead(BaseModel):
    id: UUID
    company_id: UUID
    supplier_id: Optional[UUID]
    file_type: str
    object_key: str
    sha256: str
    original_filename: Optional[str]
    uploaded_by: Optional[UUID]
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 6. ParsedDocument
# ──────────────────────────────────────────
class ParsedDocumentCreate(BaseModel):
    company_id: UUID
    inbound_file_id: UUID
    doc_kind: str = Field(..., pattern=r"^(invoice|offer|catalog|unknown)$")
    parse_status: str = "pending"
    parser_version: Optional[str] = Field(None, max_length=50)
    confidence_score: Optional[Decimal] = None
    header_json: Optional[dict] = None


class ParsedDocumentRead(BaseModel):
    id: UUID
    company_id: UUID
    inbound_file_id: UUID
    doc_kind: str
    parse_status: str
    parser_version: Optional[str]
    confidence_score: Optional[Decimal]
    header_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 7. ParsedLineItem
# ──────────────────────────────────────────
class ParsedLineItemCreate(BaseModel):
    company_id: UUID
    parsed_document_id: UUID
    line_index: int = Field(..., ge=0)
    supplier_sku_raw: Optional[str] = None
    supplier_sku_normalized: Optional[str] = None
    description_raw: Optional[str] = None
    description_normalized: Optional[str] = None
    qty: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    line_total: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    extraction_source: str = Field(
        ..., pattern=r"^(xml|pdf_ocr|pdf_table|manual)$"
    )
    extraction_notes: Optional[str] = None


class ParsedLineItemRead(BaseModel):
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

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 8. Product
# ──────────────────────────────────────────
class ProductCreate(BaseModel):
    company_id: UUID
    canonical_name: str = Field(..., max_length=500)
    internal_code: Optional[str] = Field(None, max_length=100)
    technical_specs_json: Optional[dict] = None
    category_path: Optional[str] = Field(None, max_length=500)
    status: str = "active"


class ProductUpdate(BaseModel):
    canonical_name: Optional[str] = None
    internal_code: Optional[str] = None
    technical_specs_json: Optional[dict] = None
    category_path: Optional[str] = None
    status: Optional[str] = None


class ProductRead(BaseModel):
    id: UUID
    company_id: UUID
    canonical_name: str
    internal_code: Optional[str]
    technical_specs_json: Optional[dict]
    category_path: Optional[str]
    status: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 9. ProductSupplierLink
# ──────────────────────────────────────────
class ProductSupplierLinkCreate(BaseModel):
    company_id: UUID
    product_id: UUID
    supplier_id: UUID
    supplier_sku_normalized: str = Field(..., max_length=255)
    supplier_sku_raw_examples: Optional[list] = None
    last_seen_at: Optional[datetime] = None
    price_history_json: Optional[dict] = None


class ProductSupplierLinkRead(BaseModel):
    id: UUID
    company_id: UUID
    product_id: UUID
    supplier_id: UUID
    supplier_sku_normalized: str
    supplier_sku_raw_examples: Optional[list]
    last_seen_at: Optional[datetime]
    price_history_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 10. MatchDecision
# ──────────────────────────────────────────
class MatchDecisionCreate(BaseModel):
    company_id: UUID
    parsed_line_item_id: UUID
    product_id: Optional[UUID] = None
    product_supplier_link_id: Optional[UUID] = None
    decision_type: str = Field(
        ..., pattern=r"^(auto_exact|auto_suggested|manual_confirm|manual_override)$"
    )
    candidates_json: Optional[dict] = None
    decided_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None


class MatchDecisionRead(BaseModel):
    id: UUID
    company_id: UUID
    parsed_line_item_id: UUID
    product_id: Optional[UUID]
    product_supplier_link_id: Optional[UUID]
    decision_type: str
    candidates_json: Optional[dict]
    decided_by: Optional[UUID]
    decided_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 11. EnrichmentEvent
# ──────────────────────────────────────────
class EnrichmentEventCreate(BaseModel):
    company_id: UUID
    product_id: UUID
    source_type: str = Field(
        ..., pattern=r"^(xml|list|catalog|manual|scrape)$"
    )
    source_ref: Optional[str] = None
    changes_json: Optional[dict] = None
    applied_by: Optional[UUID] = None
    applied_at: Optional[datetime] = None


class EnrichmentEventRead(BaseModel):
    id: UUID
    company_id: UUID
    product_id: UUID
    source_type: str
    source_ref: Optional[str]
    changes_json: Optional[dict]
    applied_by: Optional[UUID]
    applied_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 12. ReviewTask
# ──────────────────────────────────────────
class ReviewTaskCreate(BaseModel):
    company_id: UUID
    task_type: str = Field(
        ...,
        pattern=r"^(parse_fix|match_confirm|enrichment_confirm|export_validate)$",
    )
    entity_ref: Optional[str] = Field(None, max_length=255)
    status: str = "open"
    assigned_to: Optional[UUID] = None
    priority: str = "MEDIUM"
    payload_json: Optional[dict] = None
    resolution: Optional[str] = None


class ReviewTaskUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[UUID] = None
    priority: Optional[str] = None
    payload_json: Optional[dict] = None
    resolution: Optional[str] = None
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class ReviewTaskRead(BaseModel):
    id: UUID
    company_id: UUID
    task_type: str
    entity_ref: Optional[str]
    status: str
    assigned_to: Optional[UUID]
    priority: str
    payload_json: Optional[dict]
    resolution: Optional[str]
    resolved_by: Optional[UUID]
    resolved_at: Optional[datetime]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 13. CostUpdate
# ──────────────────────────────────────────
class CostUpdateCreate(BaseModel):
    company_id: UUID
    product_id: UUID
    product_supplier_link_id: Optional[UUID] = None
    old_cost: Optional[Decimal] = None
    new_cost: Optional[Decimal] = None
    source: str = Field(..., pattern=r"^(invoice|catalog|scrape|manual)$")
    source_ref: Optional[str] = None
    status: str = "pending"
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None


class CostUpdateRead(BaseModel):
    id: UUID
    company_id: UUID
    product_id: UUID
    product_supplier_link_id: Optional[UUID]
    old_cost: Optional[Decimal]
    new_cost: Optional[Decimal]
    source: str
    source_ref: Optional[str]
    status: str
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 14. AuditLog
# ──────────────────────────────────────────
class AuditLogCreate(BaseModel):
    company_id: UUID
    entity_type: str = Field(..., max_length=50)
    entity_id: UUID
    action: str = Field(
        ..., pattern=r"^(create|update|delete|match|enrich|export)$"
    )
    payload_json: Optional[dict] = None
    user_id: Optional[UUID] = None


class AuditLogRead(BaseModel):
    id: UUID
    company_id: UUID
    entity_type: str
    entity_id: UUID
    action: str
    payload_json: Optional[dict]
    user_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# 15. ExportJob
# ──────────────────────────────────────────
class ExportJobCreate(BaseModel):
    company_id: UUID
    export_type: str = Field(..., max_length=50)
    export_version: Optional[str] = Field(None, max_length=20)
    file_format: str = Field(..., pattern=r"^(csv|xlsx|json|xml)$")
    object_key: Optional[str] = None
    status: str = "pending"
    total_rows: Optional[int] = None
    error_message: Optional[str] = None
    requested_by: Optional[UUID] = None


class ExportJobUpdate(BaseModel):
    status: Optional[str] = None
    object_key: Optional[str] = None
    total_rows: Optional[int] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class ExportJobRead(BaseModel):
    id: UUID
    company_id: UUID
    export_type: str
    export_version: Optional[str]
    file_format: str
    object_key: Optional[str]
    status: str
    total_rows: Optional[int]
    error_message: Optional[str]
    requested_by: Optional[UUID]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Generic / Shared
# ──────────────────────────────────────────
class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    error: dict = Field(
        default_factory=lambda: {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": None,
        }
    )


class HealthResponse(BaseModel):
    status: str
    version: str
