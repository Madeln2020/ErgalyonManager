# EDM v2 Backend — Pydantic Schemas (aligned with models)

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────
# Auth & Users
# ──────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=255)
    organization_name: str = Field(..., max_length=255, description="Name of the new organization to create")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserRead(BaseModel):
    id: UUID
    email: str
    role: str
    display_name: Optional[str]
    is_active: bool
    organization_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Organization
# ──────────────────────────────────────────
class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    aade_afm: Optional[str] = Field(None, max_length=20)


class OrganizationRead(BaseModel):
    id: UUID
    name: str
    aade_afm: Optional[str]
    address: Optional[str]
    settings: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Supplier
# ──────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    legal_name: Optional[str] = Field(None, max_length=255)
    afm: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    country: str = "Greece"
    language: str = "Greek"
    website: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_persons: Optional[list] = None
    payment_terms: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    supplier_type: Optional[str] = Field(None, max_length=50)
    default_vat_rate: Optional[Decimal] = Decimal("24.00")
    default_unit: str = "ΤΕΜ"
    default_wholesale_markup: Optional[Decimal] = Decimal("30.00")
    default_retail_markup: Optional[Decimal] = Decimal("55.00")
    brands: Optional[list] = None
    default_brand: Optional[str] = Field(None, max_length=100)
    pylon_supplier_code: Optional[str] = Field(None, max_length=50)
    code_normalization_rules: Optional[dict] = None
    default_parser_id: Optional[UUID] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    legal_name: Optional[str] = None
    afm: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_persons: Optional[list] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    supplier_type: Optional[str] = None
    default_vat_rate: Optional[Decimal] = None
    default_unit: Optional[str] = None
    default_wholesale_markup: Optional[Decimal] = None
    default_retail_markup: Optional[Decimal] = None
    brands: Optional[list] = None
    default_brand: Optional[str] = None
    pylon_supplier_code: Optional[str] = None
    code_normalization_rules: Optional[dict] = None
    default_parser_id: Optional[UUID] = None
    status: Optional[str] = None


class SupplierRead(BaseModel):
    id: UUID
    name: str
    code: Optional[str]
    legal_name: Optional[str]
    afm: Optional[str]
    aade_data: Optional[dict]
    address: Optional[str]
    country: str
    language: str
    website: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    contact_persons: Optional[list]
    payment_terms: Optional[str]
    notes: Optional[str]
    supplier_type: Optional[str]
    default_vat_rate: Decimal
    default_unit: str
    default_wholesale_markup: Decimal
    default_retail_markup: Decimal
    brands: Optional[list]
    default_brand: Optional[str]
    pylon_supplier_code: Optional[str]
    status: str
    deleted_at: Optional[datetime]
    code_normalization_rules: Optional[dict]
    default_parser_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierListRead(BaseModel):
    id: UUID
    name: str
    code: Optional[str]
    afm: Optional[str]
    contact_email: Optional[str]
    default_brand: Optional[str]
    supplier_type: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# SupplierContact
# ──────────────────────────────────────────
class SupplierContactCreate(BaseModel):
    supplier_id: UUID
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class SupplierContactRead(BaseModel):
    id: UUID
    supplier_id: UUID
    name: Optional[str]
    role: Optional[str]
    phone: Optional[str]
    email: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Category
# ──────────────────────────────────────────
class CategoryCreate(BaseModel):
    level: int = Field(..., ge=1, le=3)
    name: str = Field(..., max_length=255)
    parent_id: Optional[UUID] = None
    code: Optional[str] = Field(None, max_length=50)


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
    manufacturer_code: Optional[str] = Field(None, max_length=100)
    ean: Optional[str] = Field(None, max_length=50)
    description: str
    description_normalized: Optional[str] = None
    specs_json: Optional[dict] = None
    internal_sku: Optional[str] = Field(None, max_length=100)
    pylon_code: Optional[str] = Field(None, max_length=255)
    category_k1_id: Optional[UUID] = None
    category_k2_id: Optional[UUID] = None
    category_k3_id: Optional[UUID] = None
    current_price: Optional[Decimal] = None
    price_currency: Optional[str] = Field(None, max_length=3)
    image_url: Optional[str] = None
    manufacturer_flag: bool = False


class ProductUpdate(BaseModel):
    supplier_code: Optional[str] = None
    manufacturer_code: Optional[str] = None
    ean: Optional[str] = None
    description: Optional[str] = None
    description_normalized: Optional[str] = None
    specs_json: Optional[dict] = None
    internal_sku: Optional[str] = None
    pylon_code: Optional[str] = None
    category_k1_id: Optional[UUID] = None
    category_k2_id: Optional[UUID] = None
    category_k3_id: Optional[UUID] = None
    current_price: Optional[Decimal] = None
    price_currency: Optional[str] = None
    image_url: Optional[str] = None
    manufacturer_flag: Optional[bool] = None


class ProductRead(BaseModel):
    id: UUID
    ergalyon_code: str
    supplier_code: str
    manufacturer_code: Optional[str]
    ean: Optional[str]
    supplier_id: UUID
    manufacturer_id: Optional[UUID]
    description: str
    description_normalized: str
    specs_json: Optional[dict] = None
    internal_sku: Optional[str]
    pylon_code: Optional[str]
    category_k1_id: Optional[UUID]
    category_k2_id: Optional[UUID]
    category_k3_id: Optional[UUID]
    category_confidence: Optional[Decimal]
    current_price: Optional[Decimal]
    price_currency: Optional[str]
    rag_context: Optional[dict]
    image_url: Optional[str]
    manufacturer_flag: bool
    data_completeness_score: Optional[int]
    created_by: Optional[UUID]
    updated_by: Optional[UUID]
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
    file_path: str
    file_format: str
    status: str
    parsed_data_json: Optional[dict]
    parsing_confidence: Optional[Decimal]
    total_amount: Optional[Decimal]
    currency: str
    error_message: Optional[str]
    processed_at: Optional[datetime]
    created_by: Optional[UUID]
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
    vat_rate: Optional[Decimal]
    matched_product_id: Optional[UUID]
    match_method: Optional[str]
    match_confidence: Optional[Decimal]
    manufacturer_code: Optional[str]
    status: Optional[str]
    created_at: datetime

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
    resolved_by: Optional[UUID]
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewResolve(BaseModel):
    resolution: str = Field(..., pattern="^(approved|edited|rejected)$")
    data: Optional[dict] = None
    resolved_by: Optional[UUID] = None


class ReviewQueueList(BaseModel):
    total: int
    items: list[ReviewQueueRead]


# ──────────────────────────────────────────
# Export
# ──────────────────────────────────────────
class ExportRequest(BaseModel):
    format: str = Field("xlsx", pattern="^(csv|xlsx|json|xml)$")
    supplier_id: Optional[UUID] = None
    category_k1_id: Optional[UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    export_type: str = Field("products", pattern="^(products|invoices)$")


class ExportLogRead(BaseModel):
    id: UUID
    export_type: str
    file_format: str
    file_path: Optional[str]
    status: str
    total_rows: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


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
    organization_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierAgreementSearch(BaseModel):
    query: str
    supplier_id: Optional[UUID] = None
    limit: int = 5


# ──────────────────────────────────────────
# Enrichment Queue
# ──────────────────────────────────────────
class EnrichRequest(BaseModel):
    sources: List[str] = Field(
        default=["xml", "pdf", "image", "excel", "catalog", "scraping"]
    )


class EnrichmentQueueRead(BaseModel):
    id: UUID
    product_id: UUID
    status: str
    enrichment_level: str
    source: Optional[str]
    priority: int
    payload: Optional[dict]
    result: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Parser Config
# ──────────────────────────────────────────
class ParserConfigRead(BaseModel):
    id: UUID
    name: str
    parser_type: str
    config_json: dict
    is_active: bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────
# Generic
# ──────────────────────────────────────────
class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    error: dict = Field(default_factory=lambda: {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "request_id": None,
    })


class HealthResponse(BaseModel):
    status: str
    version: str
