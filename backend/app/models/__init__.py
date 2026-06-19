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
class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    vat_number: Mapped[Optional[str]] = mapped_column(VARCHAR(20), unique=True)
    country: Mapped[str] = mapped_column(VARCHAR(2), default="GR")
    contact_email: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    rules_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    default_category_k1_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    parsing_profile: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    invoices = relationship("Invoice", back_populates="supplier")
    rules = relationship("SupplierRule", back_populates="supplier")
    agreements = relationship("SupplierAgreement", back_populates="supplier")


# ──────────────────────────────────────────────
# 5.2.2 categories
# ──────────────────────────────────────────────
class Category(Base, TimestampMixin):
    __tablename__ = "categories"

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
    invoice_items = relationship("InvoiceItem", back_populates="product")


# ──────────────────────────────────────────────
# 5.2.4 invoices
# ──────────────────────────────────────────────
class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
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

    __table_args__ = (
        Index("idx_invoices_supplier_status", "supplier_id", "status"),
    )

    # relationships
    supplier = relationship("Supplier", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


# ──────────────────────────────────────────────
# 5.2.5 invoice_items
# ──────────────────────────────────────────────
class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    raw_supplier_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    normalized_supplier_code: Mapped[Optional[str]] = mapped_column(VARCHAR(100))
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(10, 3))
    unit_price: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(10, 2))
    line_total: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 2))
    vat_rate: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    match_confidence: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))

    __table_args__ = (
        Index("idx_invoice_items_invoice", "invoice_id"),
        Index("idx_invoice_items_product", "product_id"),
    )

    # relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product", back_populates="invoice_items")


# ──────────────────────────────────────────────
# 5.2.6 product_source_data
# ──────────────────────────────────────────────
class ProductSourceData(Base, TimestampMixin):
    __tablename__ = "product_source_data"

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


# ──────────────────────────────────────────────
# 5.2.7 product_specifications
# ──────────────────────────────────────────────
class ProductSpecification(Base, TimestampMixin):
    __tablename__ = "product_specifications"

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
