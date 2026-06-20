# EDM v2 — Core SQLAlchemy Models
# Based on §5 Database Design

import uuid
from datetime import datetime, timezone
from decimal import Decimal as PyDecimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    Text,
    UniqueConstraint,
    VARCHAR,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.database import Base


# ──────────────────────────────────────────────
# Mixins
# ──────────────────────────────────────────────
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)


# ──────────────────────────────────────────────
# 5.2.1 suppliers
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# 5.2.0 organizations
# ──────────────────────────────────────────────
class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    aade_afm: Mapped[Optional[str]] = mapped_column(VARCHAR(20), unique=True)
    address: Mapped[Optional[Text]] = mapped_column(Text)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    users = relationship("User", back_populates="organization")
    suppliers = relationship("Supplier", back_populates="organization")
    products = relationship("Product", back_populates="organization")
    invoices = relationship("Invoice", back_populates="organization")

# ──────────────────────────────────────────────
# 5.2.0 users
# ──────────────────────────────────────────────
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    role: Mapped[str] = mapped_column(VARCHAR(20))  # Should be restricted to OWNER, ADMIN, USER, VIEWER via check constraint or enum
    display_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # relationships
    organization = relationship("Organization", back_populates="users")
class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)  # Display Name
    legal_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    afm: Mapped[Optional[str]] = mapped_column(VARCHAR(20), unique=True)  # AADE Tax ID (ΑΦΜ)
    aade_data: Mapped[Optional[dict]] = mapped_column(JSONB)  # cached JSON: DOY, address, registration status, activity codes
    website: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    contact_email: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    contact_persons: Mapped[Optional[list]] = mapped_column(JSONB)  # list of dicts: {name, role, phone, email}
    payment_terms: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    notes: Mapped[Optional[Text]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('ACTIVE','INACTIVE','BLACKLISTED')"),
        default='ACTIVE'
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # Soft delete
    code_normalization_rules: Mapped[Optional[dict]] = mapped_column(JSONB)  # JSON config for regex transformations
    default_parser_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parser_configs.id")
    )
    # Timestamps from TimestampMixin: created_at, updated_at

    # relationships
    invoices = relationship("Invoice", back_populates="supplier")
    rules = relationship("SupplierRule", back_populates="supplier")
    agreements = relationship("SupplierAgreement", back_populates="supplier")
    contacts = relationship("SupplierContact", back_populates="supplier", cascade="all, delete-orphan")
    organization = relationship("Organization")


# ──────────────────────────────────────────────
# 4.5 supplier_contacts
# ──────────────────────────────────────────────
class SupplierContact(Base, TimestampMixin):
    __tablename__ = "supplier_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    role: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    phone: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    email: Mapped[Optional[str]] = mapped_column(VARCHAR(255))

    # relationships
    supplier = relationship("Supplier", back_populates="contacts")
    organization = relationship("Organization")


# ──────────────────────────────────────────────
# 5.2.2 categories

# ──────────────────────────────────────────────
class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    level: Mapped[int] = mapped_column(
        SmallInteger, CheckConstraint("level IN (1, 2, 3)"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT")
    )
    code: Mapped[Optional[str]] = mapped_column(VARCHAR(50))

    __table_args__ = (
        CheckConstraint(
            "(level = 1 AND parent_id IS NULL) OR (level > 1 AND parent_id IS NOT NULL)",
            name="chk_level1_no_parent",
        ),
    )


# ──────────────────────────────────────────────
# 5.2.3 products
# ──────────────────────────────────────────────
class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    ergalyon_code: Mapped[str] = mapped_column(VARCHAR(50), unique=True, nullable=False)
    supplier_code: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    manufacturer_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    ean: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    manufacturer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    specs_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    internal_sku: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    pylon_code: Mapped[Optional[str]] = mapped_column(VARCHAR(255))  # ONLY for export
    category_k1_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    category_k2_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    category_k3_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    category_confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    current_price: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(10, 2))
    price_currency: Mapped[Optional[str]] = mapped_column(VARCHAR(3))
    rag_context: Mapped[Optional[dict]] = mapped_column(JSONB)
    embedding: Mapped[Optional[dict]] = mapped_column(JSONB)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    manufacturer_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    data_completeness_score: Mapped[Optional[int]] = mapped_column(
        SmallInteger, CheckConstraint("data_completeness_score BETWEEN 0 AND 100")
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("supplier_id", "supplier_code", name="uq_supplier_code"),
        Index("idx_products_supplier_code", "supplier_id", "supplier_code"),
        Index("idx_products_manufacturer", "manufacturer_code"),
        Index("idx_products_ean", "ean"),
        Index("idx_products_categories", "category_k1_id", "category_k2_id", "category_k3_id"),
    )

    # relationships
    supplier = relationship("Supplier")
    specs = relationship("ProductSpecification", back_populates="product")
    source_data = relationship("ProductSourceData", back_populates="product")
    price_history = relationship("PriceHistory", back_populates="product")
    review_items = relationship("ReviewQueueItem", back_populates="product")
    invoice_items = relationship("InvoiceItem", back_populates="product", foreign_keys="InvoiceItem.product_id")
    organization = relationship("Organization")
# 5.2.4 invoices
# ──────────────────────────────────────────────
class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("document_type IN ('invoice','offer','catalog')"),
        default="invoice",
    )
    invoice_number: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    invoice_date: Mapped[Optional[datetime]] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_format: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("file_format IN ('xml','pdf','image','excel','catalog')"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(30),
        CheckConstraint(
            "status IN ('uploaded','parsing','parsed','normalized','enriched','reviewed','exported','failed')"
        ),
        default="uploaded",
    )
    parsed_data_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    parsing_confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    total_amount: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 2))
    currency: Mapped[str] = mapped_column(VARCHAR(3), default="EUR")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_invoices_supplier_status", "supplier_id", "status"),
    )

    # relationships
    supplier = relationship("Supplier", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    organization = relationship("Organization")
# 5.2.5 invoice_items
# ──────────────────────────────────────────────
class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=False
    )
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    raw_supplier_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    normalized_supplier_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(10, 3))
    unit_price: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(10, 2))
    line_total: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 2))
    vat_rate: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    matched_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id")
    )
    match_method: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("match_method IN ('BARCODE','EXACT_CODE','NORMALIZED_CODE','FUZZY','MANUAL','NONE')"),
        nullable=True
    )
    match_confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    manufacturer_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('PENDING','MATCHED','NEW_PRODUCT','MANUAL_REVIEW')"),
        nullable=True
    )

    __table_args__ = (
        Index("idx_invoice_items_invoice", "invoice_id"),
        Index("idx_invoice_items_product", "product_id"),
    )

    # relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items", foreign_keys="InvoiceItem.product_id")
    organization = relationship("Organization")
# 5.2.6 product_source_data
# ──────────────────────────────────────────────
class ProductSourceData(Base, TimestampMixin):
    __tablename__ = "product_source_data"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("source IN ('xml','catalog','manual','scraping')"),
        nullable=False,
    )
    source_priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("idx_source_active", "product_id", "field_name", postgresql_where=text("is_active")),
    )

    # relationships
    product = relationship("Product", back_populates="source_data")
    organization = relationship("Organization")


# ──────────────────────────────────────────────
# 5.2.7 product_specifications
# ──────────────────────────────────────────────
class ProductSpecification(Base, TimestampMixin):
    __tablename__ = "product_specifications"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    spec_key: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    spec_value: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    source: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("source IN ('xml','catalog','manual','scraping')"),
        nullable=False,
    )
    source_confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))

    __table_args__ = (
        UniqueConstraint("product_id", "spec_key", name="uq_product_spec"),
    )

    # relationships
    product = relationship("Product", back_populates="specs")


# ──────────────────────────────────────────────
# 5.2.8 price_history
# ──────────────────────────────────────────────
class PriceHistory(Base):
    __tablename__ = "price_history"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[PyDecimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(VARCHAR(3), default="EUR")
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id")
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_price_history_product", "product_id", "recorded_at"),
    )

    # relationships
    product = relationship("Product", back_populates="price_history")


# ──────────────────────────────────────────────
# 5.2.9 supplier_rules
# ──────────────────────────────────────────────
class SupplierRule(Base, TimestampMixin):
    __tablename__ = "supplier_rules"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(
        VARCHAR(50),
        CheckConstraint(
            "rule_type IN ('code_normalization','field_mapping','validation','enrichment_hint')"
        ),
        nullable=False,
    )
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    supplier = relationship("Supplier", back_populates="rules")


# ──────────────────────────────────────────────
# 5.2.10 supplier_agreements
# ──────────────────────────────────────────────
class SupplierAgreement(Base, TimestampMixin):
    __tablename__ = "supplier_agreements"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[Optional[datetime]] = mapped_column(Date)
    valid_to: Mapped[Optional[datetime]] = mapped_column(Date)
    rag_index_id: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # relationships
    supplier = relationship("Supplier", back_populates="agreements")


# ──────────────────────────────────────────────
# 5.2.11 review_queue
# ──────────────────────────────────────────────
class ReviewQueueItem(Base, TimestampMixin):
    __tablename__ = "review_queue"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    invoice_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoice_items.id", ondelete="CASCADE")
    )
    review_type: Mapped[str] = mapped_column(
        VARCHAR(50),
        CheckConstraint(
            "review_type IN ('low_confidence','duplicate','missing_manufacturer_code','price_anomaly','new_supplier')"
        ),
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("priority IN ('CRITICAL','HIGH','MEDIUM','LOW')"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('open','in_progress','resolved','dismissed')"),
        default="open",
    )
    payload_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text)
    resolution: Mapped[Optional[str]] = mapped_column(
        VARCHAR(50),
        CheckConstraint("resolution IN ('approved','edited','rejected')"),
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_review_open_priority", "status", "priority",
              postgresql_where=text("status IN ('open', 'in_progress')")),
    )

    # relationships
    product = relationship("Product", back_populates="review_items")


# ──────────────────────────────────────────────
# 5.2.12 audit_log
# ──────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    entity_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ──────────────────────────────────────────────
# 5.2.13 parser_configs
# ──────────────────────────────────────────────
class ParserConfig(Base, TimestampMixin):
    __tablename__ = "parser_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    parser_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # relationships
    organization = relationship("Organization")


# ──────────────────────────────────────────────
# 5.2.14 enrichment_queue
# ──────────────────────────────────────────────
class EnrichmentQueueItem(Base):
    __tablename__ = "enrichment_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    enrichment_level: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("enrichment_level IN ('XML','CATALOG','PRODUCT_LIST','MANUAL','WEB_SCRAPING')"),
        nullable=False,
    )
    source: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')"),
        default="PENDING",
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    result: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    product = relationship("Product")


# ──────────────────────────────────────────────
# 5.2.15 export_logs
# ──────────────────────────────────────────────
class ExportLog(Base):
    __tablename__ = "export_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    export_type: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    file_format: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(VARCHAR(500))
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('PENDING','PROCESSING','COMPLETED','FAILED')"),
        nullable=False,
    )
    total_rows: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # relationships
    organization = relationship("Organization")


# ──────────────────────────────────────────────
# 5.2.16 scrape_configs
# ──────────────────────────────────────────────
class ScrapeConfig(Base, TimestampMixin):
    __tablename__ = "scrape_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    strategy: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("strategy IN ('CRAWL4AI','PLAYWRIGHT','SCRAPY','MANUAL')"),
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # relationships
    supplier = relationship("Supplier")
    organization = relationship("Organization")
