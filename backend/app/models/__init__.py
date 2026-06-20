# ═══════════════════════════════════════════════════════════════════════
# EDM v2.1 — SQLAlchemy ORM Models (15 tables, multi-tenant)
# All tables include company_id for tenant isolation.
# All PKs are UUID with gen_random_uuid().
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal as PyDecimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    DECIMAL,
    ForeignKey,
    Index,
    Integer,
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
    """Adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds is_deleted flag for soft deletes."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )


# ──────────────────────────────────────────────
# 1. Company (multi-tenancy root)
# ──────────────────────────────────────────────
class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    vat_number: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    settings_json: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # relationships
    users = relationship("User", back_populates="company")
    suppliers = relationship("Supplier", back_populates="company")
    supplier_documents = relationship("SupplierDocument", back_populates="company")
    inbound_files = relationship("InboundFile", back_populates="company")
    parsed_documents = relationship("ParsedDocument", back_populates="company")
    parsed_line_items = relationship("ParsedLineItem", back_populates="company")
    products = relationship("Product", back_populates="company")
    product_supplier_links = relationship(
        "ProductSupplierLink", back_populates="company"
    )
    match_decisions = relationship("MatchDecision", back_populates="company")
    enrichment_events = relationship("EnrichmentEvent", back_populates="company")
    review_tasks = relationship("ReviewTask", back_populates="company")
    cost_updates = relationship("CostUpdate", back_populates="company")
    audit_logs = relationship("AuditLog", back_populates="company")
    export_jobs = relationship("ExportJob", back_populates="company")


# ──────────────────────────────────────────────
# 2. User
# ──────────────────────────────────────────────
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    role: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("role IN ('viewer','user','admin','owner')"),
        nullable=False,
    )
    display_name: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_user_company_email"),
        Index("idx_users_company", "company_id"),
        Index("idx_users_email", "email"),
    )

    # relationships
    company = relationship("Company", back_populates="users")


# ──────────────────────────────────────────────
# 3. Supplier
# ──────────────────────────────────────────────
class Supplier(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    vat_number: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    tax_profile_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="AADE / tax authority profile"
    )
    contacts_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="List of contact persons"
    )
    default_currency: Mapped[str] = mapped_column(
        VARCHAR(3), default="EUR", server_default=text("'EUR'"), nullable=False
    )
    default_parser: Mapped[Optional[str]] = mapped_column(
        VARCHAR(50), comment="Default parsing profile"
    )
    rules_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Code normalization & validation rules"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("company_id", "vat_number", name="uq_company_vat"),
        Index("idx_suppliers_company", "company_id"),
        Index("idx_suppliers_vat", "vat_number"),
    )

    # relationships
    company = relationship("Company", back_populates="suppliers")
    documents = relationship("SupplierDocument", back_populates="supplier")
    inbound_files = relationship("InboundFile", back_populates="supplier")
    product_links = relationship("ProductSupplierLink", back_populates="supplier")


# ──────────────────────────────────────────────
# 4. SupplierDocument
# ──────────────────────────────────────────────
class SupplierDocument(Base, TimestampMixin):
    __tablename__ = "supplier_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("doc_type IN ('agreement','catalog','price_list','other')"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(
        Text, nullable=False, comment="MinIO object key"
    )
    title: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    extracted_text_object_key: Mapped[Optional[str]] = mapped_column(
        Text, comment="MinIO key for extracted text"
    )
    embedding_ref: Mapped[Optional[str]] = mapped_column(
        VARCHAR(255), comment="Vector embedding reference"
    )

    __table_args__ = (
        Index("idx_supplier_docs_supplier", "supplier_id"),
        Index("idx_supplier_docs_company", "company_id"),
        Index("idx_supplier_docs_type", "doc_type"),
    )

    # relationships
    supplier = relationship("Supplier", back_populates="documents")
    company = relationship("Company", back_populates="supplier_documents")


# ──────────────────────────────────────────────
# 5. InboundFile
# ──────────────────────────────────────────────
class InboundFile(Base, TimestampMixin):
    __tablename__ = "inbound_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    file_type: Mapped[str] = mapped_column(
        VARCHAR(10),
        CheckConstraint("file_type IN ('pdf','xml','xlsx','img')"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(
        Text, nullable=False, comment="MinIO object key"
    )
    sha256: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(VARCHAR(500))
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_inbound_files_company", "company_id"),
        Index("idx_inbound_files_supplier", "supplier_id"),
        Index("idx_inbound_files_sha256", "sha256"),
        Index("idx_inbound_files_type", "file_type"),
    )

    # relationships
    company = relationship("Company", back_populates="inbound_files")
    supplier = relationship("Supplier", back_populates="inbound_files")
    parsed_documents = relationship("ParsedDocument", back_populates="inbound_file")


# ──────────────────────────────────────────────
# 6. ParsedDocument
# ──────────────────────────────────────────────
class ParsedDocument(Base, TimestampMixin):
    __tablename__ = "parsed_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    inbound_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inbound_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    doc_kind: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("doc_kind IN ('invoice','offer','catalog','unknown')"),
        nullable=False,
    )
    parse_status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "parse_status IN ('pending','success','needs_review','failed')"
        ),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )
    parser_version: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    confidence_score: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    header_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Date, doc_number, totals"
    )

    __table_args__ = (
        Index("idx_parsed_docs_company", "company_id"),
        Index("idx_parsed_docs_inbound", "inbound_file_id"),
        Index("idx_parsed_docs_status", "parse_status"),
        Index("idx_parsed_docs_kind", "doc_kind"),
    )

    # relationships
    company = relationship("Company", back_populates="parsed_documents")
    inbound_file = relationship("InboundFile", back_populates="parsed_documents")
    line_items = relationship(
        "ParsedLineItem",
        back_populates="parsed_document",
        cascade="all, delete-orphan",
    )


# ──────────────────────────────────────────────
# 7. ParsedLineItem
# ──────────────────────────────────────────────
class ParsedLineItem(Base, TimestampMixin):
    __tablename__ = "parsed_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    parsed_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parsed_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    supplier_sku_raw: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    supplier_sku_normalized: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    description_raw: Mapped[Optional[str]] = mapped_column(Text)
    description_normalized: Mapped[Optional[str]] = mapped_column(Text)
    qty: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 3))
    unit_price: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 4))
    line_total: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(14, 2))
    vat_rate: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(5, 2))
    extraction_source: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "extraction_source IN ('xml','pdf_ocr','pdf_table','manual')"
        ),
        nullable=False,
    )
    extraction_notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_pli_parsed_doc", "parsed_document_id"),
        Index("idx_pli_company", "company_id"),
        Index("idx_pli_sku", "supplier_sku_normalized"),
    )

    # relationships
    company = relationship("Company", back_populates="parsed_line_items")
    parsed_document = relationship("ParsedDocument", back_populates="line_items")
    match_decisions = relationship(
        "MatchDecision",
        back_populates="parsed_line_item",
        cascade="all, delete-orphan",
    )


# ──────────────────────────────────────────────
# 8. Product
# ──────────────────────────────────────────────
class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(VARCHAR(500), nullable=False)
    internal_code: Mapped[Optional[str]] = mapped_column(
        VARCHAR(100), comment="EDM internal code (e.g., ERG-00000001)"
    )
    technical_specs_json: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    category_path: Mapped[Optional[str]] = mapped_column(
        VARCHAR(500), comment="Hierarchical path e.g. K1/K2/K3"
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('active','provisional','archived')"),
        default="active",
        server_default=text("'active'"),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_products_company", "company_id"),
        Index("idx_products_internal_code", "internal_code"),
        Index("idx_products_status", "status"),
    )

    # relationships
    company = relationship("Company", back_populates="products")
    supplier_links = relationship(
        "ProductSupplierLink", back_populates="product", cascade="all, delete-orphan"
    )
    enrichment_events = relationship(
        "EnrichmentEvent", back_populates="product", cascade="all, delete-orphan"
    )
    cost_updates = relationship(
        "CostUpdate", back_populates="product", cascade="all, delete-orphan"
    )


# ──────────────────────────────────────────────
# 9. ProductSupplierLink
# ──────────────────────────────────────────────
class ProductSupplierLink(Base, TimestampMixin):
    __tablename__ = "product_supplier_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_sku_normalized: Mapped[str] = mapped_column(
        VARCHAR(255), nullable=False, comment="Normalized SKU (unique per supplier)"
    )
    supplier_sku_raw_examples: Mapped[Optional[list]] = mapped_column(
        JSONB, comment="Array of raw SKU examples"
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    price_history_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Price history snapshot"
    )

    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "supplier_sku_normalized",
            name="uq_sku_per_supplier",
        ),
        Index("idx_psl_company", "company_id"),
        Index("idx_psl_product", "product_id"),
        Index("idx_psl_supplier", "supplier_id"),
        Index("idx_psl_sku", "supplier_sku_normalized"),
    )

    # relationships
    company = relationship("Company", back_populates="product_supplier_links")
    product = relationship("Product", back_populates="supplier_links")
    supplier = relationship("Supplier", back_populates="product_links")
    match_decisions = relationship(
        "MatchDecision", back_populates="product_supplier_link"
    )
    cost_updates = relationship(
        "CostUpdate", back_populates="product_supplier_link"
    )


# ──────────────────────────────────────────────
# 10. MatchDecision
# ──────────────────────────────────────────────
class MatchDecision(Base, TimestampMixin):
    __tablename__ = "match_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    parsed_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parsed_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    product_supplier_link_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_supplier_links.id", ondelete="SET NULL"),
    )
    decision_type: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "decision_type IN ('auto_exact','auto_suggested','manual_confirm','manual_override')"
        ),
        nullable=False,
    )
    candidates_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_md_line_item", "parsed_line_item_id"),
        Index("idx_md_product", "product_id"),
        Index("idx_md_company", "company_id"),
        Index("idx_md_type", "decision_type"),
    )

    # relationships
    company = relationship("Company", back_populates="match_decisions")
    parsed_line_item = relationship("ParsedLineItem", back_populates="match_decisions")
    product = relationship("Product")
    product_supplier_link = relationship(
        "ProductSupplierLink", back_populates="match_decisions"
    )


# ──────────────────────────────────────────────
# 11. EnrichmentEvent
# ──────────────────────────────────────────────
class EnrichmentEvent(Base, TimestampMixin):
    __tablename__ = "enrichment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "source_type IN ('xml','list','catalog','manual','scrape')"
        ),
        nullable=False,
    )
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    changes_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Diff of changes applied"
    )
    applied_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_ee_product", "product_id"),
        Index("idx_ee_company", "company_id"),
        Index("idx_ee_source", "source_type"),
    )

    # relationships
    company = relationship("Company", back_populates="enrichment_events")
    product = relationship("Product", back_populates="enrichment_events")


# ──────────────────────────────────────────────
# 12. ReviewTask
# ──────────────────────────────────────────────
class ReviewTask(Base, TimestampMixin):
    __tablename__ = "review_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(
        VARCHAR(30),
        CheckConstraint(
            "task_type IN ('parse_fix','match_confirm','enrichment_confirm','export_validate')"
        ),
        nullable=False,
    )
    entity_ref: Mapped[Optional[str]] = mapped_column(
        VARCHAR(255), comment="Polymorphic reference: table_name:pk"
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('open','in_progress','done')"),
        default="open",
        server_default=text("'open'"),
        nullable=False,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    priority: Mapped[str] = mapped_column(
        VARCHAR(10),
        CheckConstraint("priority IN ('CRITICAL','HIGH','MEDIUM','LOW')"),
        default="MEDIUM",
        server_default=text("'MEDIUM'"),
        nullable=False,
    )
    payload_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_rt_company", "company_id"),
        Index("idx_rt_type", "task_type"),
        Index("idx_rt_status", "status"),
        Index("idx_rt_assigned", "assigned_to"),
        Index("idx_rt_priority", "priority"),
    )

    # relationships
    company = relationship("Company", back_populates="review_tasks")


# ──────────────────────────────────────────────
# 13. CostUpdate
# ──────────────────────────────────────────────
class CostUpdate(Base, TimestampMixin):
    __tablename__ = "cost_updates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_supplier_link_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_supplier_links.id", ondelete="SET NULL"),
    )
    old_cost: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 4))
    new_cost: Mapped[Optional[PyDecimal]] = mapped_column(DECIMAL(12, 4))
    source: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("source IN ('invoice','catalog','scrape','manual')"),
        nullable=False,
    )
    source_ref: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint("status IN ('pending','approved','rejected')"),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_cu_product", "product_id"),
        Index("idx_cu_company", "company_id"),
        Index("idx_cu_status", "status"),
    )

    # relationships
    company = relationship("Company", back_populates="cost_updates")
    product = relationship("Product", back_populates="cost_updates")
    product_supplier_link = relationship(
        "ProductSupplierLink", back_populates="cost_updates"
    )


# ──────────────────────────────────────────────
# 14. AuditLog
# ──────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        VARCHAR(50), nullable=False, comment="Table/entity name"
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    action: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "action IN ('create','update','delete','match','enrich','export')"
        ),
        nullable=False,
    )
    payload_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_al_company", "company_id"),
        Index("idx_al_entity", "entity_type", "entity_id"),
        Index("idx_al_action", "action"),
        Index("idx_al_user", "user_id"),
        Index("idx_al_created", "created_at"),
    )

    # relationships
    company = relationship("Company", back_populates="audit_logs")


# ──────────────────────────────────────────────
# 15. ExportJob
# ──────────────────────────────────────────────
class ExportJob(Base, TimestampMixin):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    export_type: Mapped[str] = mapped_column(
        VARCHAR(50), nullable=False, comment="e.g. products, price_list"
    )
    export_version: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    file_format: Mapped[str] = mapped_column(
        VARCHAR(10),
        CheckConstraint("file_format IN ('csv','xlsx','json','xml')"),
        nullable=False,
    )
    object_key: Mapped[Optional[str]] = mapped_column(
        Text, comment="MinIO object key for export output"
    )
    status: Mapped[str] = mapped_column(
        VARCHAR(20),
        CheckConstraint(
            "status IN ('pending','processing','completed','failed')"
        ),
        default="pending",
        server_default=text("'pending'"),
        nullable=False,
    )
    total_rows: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_ej_company", "company_id"),
        Index("idx_ej_type", "export_type"),
        Index("idx_ej_status", "status"),
    )

    # relationships
    company = relationship("Company", back_populates="export_jobs")
