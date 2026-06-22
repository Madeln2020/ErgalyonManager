# EDM v2.1 — Enrichment Queue Item
# Tracks products awaiting enrichment processing
from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class EnrichmentSource(str, PyEnum):
    """Source of enrichment trigger."""
    XML = "xml"
    MANUAL = "manual"
    WEB_SCRAPING = "web_scraping"
    ALL = "all"


class EnrichmentLevel(str, PyEnum):
    """Level of enrichment to process."""
    XML = "XML"
    CATALOG = "CATALOG"
    PRODUCT_LIST = "PRODUCT_LIST"
    MANUAL = "MANUAL"
    WEB_SCRAPING = "WEB_SCRAPING"


class EnrichmentStatus(str, PyEnum):
    """Status of enrichment processing."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EnrichmentQueueItem(Base, TimestampMixin):
    """
    Queue item for product enrichment processing.
    
    Tracks which products need enrichment and at what level.
    """
    __tablename__ = "enrichment_queue_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    
    # Who/what triggered this enrichment
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    
    # What type of enrichment triggered this
    source: Mapped[Optional[str]] = mapped_column(
        String(20),  # Matches EnrichmentSource values
        nullable=True
    )
    
    # Which enrichment level to process (NULL = all levels)
    enrichment_level: Mapped[Optional[str]] = mapped_column(
        String(20),  # Matches EnrichmentLevel values
        nullable=True
    )
    
    # Processing status
    status: Mapped[str] = mapped_column(
        String(20),  # Matches EnrichmentStatus values
        nullable=False,
        server_default=text("'PENDING'"),
        index=True
    )
    
    # Processing timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Error information if failed
    error_message: Mapped[Optional[Text]] = mapped_column(
        Text, nullable=True
    )
    
    # Results of enrichment processing
    result: Mapped[Optional[JSONB]] = mapped_column(
        JSONB, nullable=True
    )
    
    # References to source data (e.g., XML file ID, manual notes ID, etc.)
    source_ref: Mapped[Optional[String]] = mapped_column(
        String(255), nullable=True
    )
    
    # Relationships
    company = relationship("Company", back_populates="enrichment_queue")
    product = relationship("Product", back_populates="enrichment_queue")
    
    # Indexes
    __table_args__ = (
        Index("eqi_company_status", "company_id", "status"),
        Index("eqi_product_status", "product_id", "status"),
        Index("eqi_source_level", "source", "enrichment_level"),
    )


# Add back-references to related models
# These will be appended to the respective model classes after definition
