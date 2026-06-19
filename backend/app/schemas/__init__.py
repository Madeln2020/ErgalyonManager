# EDM v2 Backend — Pydantic Schemas

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# Supplier
# ──────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=255)
    vat_number: Optional[str] = Field(None, max_length=20)
    country: str = "GR"
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    rules_json: dict = {}
    parsing_profile: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    rules_json: Optional[dict] = None
    parsing_profile: Optional[str] = None
    is_active: Optional[bool] = None


class SupplierRead(BaseModel):
    id: UUID
    name: str
    vat_number: Optional[str]
    country: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    rules_json: dict = {}
    parsing_profile: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Category
# ──────────────────────────────────────────
class CategoryRead(BaseModel):
    id: UUID
    level: int
    name: str
    parent_id: Optional[UUID]
    code: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Product
# ──────────────────────────────────────────
class ProductCreate(BaseModel):
    supplier_id: UUID
    supplier_code: str = Field(..., max_length=100)
    manufacturer_code: Optional[str] = None
    ean: Optional[str] = None
    description: str
    description_normalized: Optional[str] = None
    current_price: Optional[Decimal] = None
    category_k1_id: Optional[UUID] = None
    category_k2_id: Optional[UUID] = None
    category_k3_id: Optional[UUID] = None


class ProductUpdate(BaseModel):
    manufacturer_code: Optional[str] = None
    ean: Optional[str] = None
    description: Optional[str] = None
    current_price: Optional[Decimal] = None
    category_k1_id: Optional[UUID] = None
    category_k2_id: Optional[UUID] = None
    category_k3_id: Optional[UUID] = None


class ProductRead(BaseModel):
    id: UUID
    ergalyon_code: str
    supplier_code: str
    manufacturer_code: Optional[str]
    ean: Optional[str]
    supplier_id: UUID
    description: str
    description_normalized: str
    category_k1_id: Optional[UUID]
    category_k2_id: Optional[UUID]
    category_k3_id: Optional[UUID]
    category_confidence: Optional[Decimal]
    current_price: Optional[Decimal]
    price_currency: Optional[str]
    image_url: Optional[str]
    manufacturer_flag: bool
    data_completeness_score: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int


# ──────────────────────────────────────────
# Invoice
# ──────────────────────────────────────────
class InvoiceUpload(BaseModel):
    supplier_id: UUID
    document_type: str = "invoice"


class InvoiceRead(BaseModel):
    id: UUID
    supplier_id: UUID
    document_type: str
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    file_format: str
    status: str
    parsing_confidence: Optional[Decimal]
    total_amount: Optional[Decimal]
    currency: str
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceItemRead(BaseModel):
    id: UUID
    invoice_id: UUID
    product_id: Optional[UUID]
    line_number: Optional[int]
    raw_supplier_code: Optional[str]
    normalized_supplier_code: Optional[str]
    raw_description: str
    quantity: Optional[Decimal]
    unit_price: Optional[Decimal]
    line_total: Optional[Decimal]
    match_confidence: Optional[Decimal]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Review Queue
# ──────────────────────────────────────────
class ReviewQueueRead(BaseModel):
    id: UUID
    product_id: Optional[UUID]
    invoice_item_id: Optional[UUID]
    review_type: str
    priority: str
    status: str
    payload_json: Optional[dict]
    prompt_text: Optional[str]
    resolution: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewResolve(BaseModel):
    resolution: str = Field(..., pattern="^(approved|edited|rejected)$")
    data: Optional[dict] = None


class ReviewQueueList(BaseModel):
    total: int
    items: list[ReviewQueueRead]


# ──────────────────────────────────────────
# Export
# ──────────────────────────────────────────
class ExportRequest(BaseModel):
    format: str = Field("csv", pattern="^(csv|excel|json|xml)$")
    supplier_id: Optional[UUID] = None
    category_k1_id: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
review_status: Optional[str] = None

# ──────────────────────────────────────────
# Supplier Agreement
# ──────────────────────────────────────────
class SupplierAgreementCreate(BaseModel):
    supplier_id: UUID
    title: Optional[str] = Field(None, max_length=255)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class SupplierAgreementRead(BaseModel):
    id: UUID
    supplier_id: UUID
    title: Optional[str]
    file_path: str
    valid_from: Optional[date]
    valid_to: Optional[date]
    rag_index_id: Optional[str]
    indexed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierAgreementSearch(BaseModel):
    query: str
    supplier_id: Optional[UUID] = None
    limit: int = 5


# ──────────────────────────────────────────
# Enrichment
# ──────────────────────────────────────────
class EnrichRequest(BaseModel):
    sources: List[str] = Field(default=["xml", "pdf", "image", "excel", "catalog", "scraping"])
    # Optional list of sources to use for enrichment; if empty, use all
    # Each source corresponds to a parser: xml, pdf, image, excel, catalog, scraping


# ──────────────────────────────────────────
# Generic
# ──────────────────────────────────────────
class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class ErrorResponse(BaseModel):
    error: dict = Field(default_factory=lambda: {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "request_id": None,
    })
