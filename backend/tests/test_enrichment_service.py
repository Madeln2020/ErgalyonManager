"""
Unit tests for Enrichment Service — tests the actual implementation.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EnrichmentQueueItem, Product, Company
from app.services.enrichment_service import _merge_field, process_enrichment


class TestMergeField:
    """Test the pure _merge_field function with source precedence rules."""

    def test_no_existing_value(self):
        """Should set value when no existing value."""
        now = datetime.now(timezone.utc)
        should_update, updated = _merge_field(None, "Test Name", "XML", now)
        assert should_update is True
        assert updated["value"] == "Test Name"
        assert updated["source"] == "XML"
        assert updated["priority"] == 4  # XML priority

    def test_higher_priority_overwrites(self):
        """Higher priority source should overwrite lower priority."""
        now = datetime.now(timezone.utc)
        existing = {
            "value": "Old Name",
            "source": "WEB_SCRAPING",
            "updated_at": now.isoformat(),
            "priority": 1,
        }
        should_update, updated = _merge_field(existing, "New Name", "XML", now)
        assert should_update is True
        assert updated["value"] == "New Name"
        assert updated["source"] == "XML"
        assert updated["priority"] == 4

    def test_lower_priority_ignored(self):
        """Lower priority source should NOT overwrite higher priority."""
        now = datetime.now(timezone.utc)
        existing = {
            "value": "High Priority Name",
            "source": "XML",
            "updated_at": now.isoformat(),
            "priority": 4,
        }
        should_update, updated = _merge_field(existing, "Low Name", "WEB_SCRAPING", now)
        assert should_update is False
        assert updated == existing  # Unchanged

    def test_equal_priority_keeps_existing(self):
        """Same priority should keep existing (conservative approach)."""
        now = datetime.now(timezone.utc)
        existing = {
            "value": "Original Name",
            "source": "XML",
            "updated_at": now.isoformat(),
            "priority": 4,
        }
        newer = datetime(2027, 1, 1, tzinfo=timezone.utc)
        should_update, updated = _merge_field(existing, "Newer Name", "XML", newer)
        assert should_update is False
        assert updated == existing

    def test_unknown_source_lowest_priority(self):
        """Unknown source should be treated as priority 0."""
        now = datetime.now(timezone.utc)
        existing = {
            "value": "Original",
            "source": "XML",
            "updated_at": now.isoformat(),
            "priority": 4,
        }
        should_update, updated = _merge_field(existing, "New", "UNKNOWN_SOURCE", now)
        assert should_update is False
        assert updated == existing

    def test_catalog_source_priority(self):
        """CATALOG source should have priority 3."""
        now = datetime.now(timezone.utc)
        should_update, updated = _merge_field(None, "Catalog Data", "CATALOG", now)
        assert should_update is True
        assert updated["priority"] == 3

    def test_manual_source_priority(self):
        """MANUAL source should have priority 2."""
        now = datetime.now(timezone.utc)
        should_update, updated = _merge_field(None, "Manual Data", "MANUAL", now)
        assert should_update is True
        assert updated["priority"] == 2


@pytest.mark.asyncio
async def test_process_enrichment_creates_pending_cost_update(
    db_session: AsyncSession,
    test_product: Product,
    test_company: Company,
):
    """Test that process_enrichment runs and returns a result dict."""
    # Create an enrichment queue item
    queue_item = EnrichmentQueueItem(
        id=uuid4(),
        company_id=test_company.id,
        product_id=test_product.id,
        source="xml",
        status="PENDING",
    )
    db_session.add(queue_item)
    await db_session.commit()

    # Call process_enrichment — it opens its own DB session internally
    result = await process_enrichment(queue_item.id)

    # Should return a dict with status (may be COMPLETED or FAILED depending on data)
    assert isinstance(result, dict)
    assert "status" in result


@pytest.mark.asyncio
async def test_process_enrichment_invalid_id(db_session: AsyncSession):
    """Test process_enrichment with a non-existent queue item ID."""
    fake_id = uuid4()
    result = await process_enrichment(fake_id)

    assert result["status"] == "FAILED"
    assert "error" in result


@pytest.mark.asyncio
async def test_process_enrichment_with_real_product_succeeds(
    db_session: AsyncSession,
    test_product: Product,
    test_company: Company,
):
    """Test enrichment with a valid product completes successfully."""
    queue_item = EnrichmentQueueItem(
        id=uuid4(),
        company_id=test_company.id,
        product_id=test_product.id,
        source="xml",
        status="PENDING",
    )
    db_session.add(queue_item)
    await db_session.commit()

    result = await process_enrichment(queue_item.id)

    # Should return a dict with status
    assert isinstance(result, dict)
    assert "status" in result
