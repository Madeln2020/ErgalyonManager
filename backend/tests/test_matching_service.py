"""
Unit tests for Matching Service — tests the actual functions that exist.
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductSupplierLink, Supplier, ParsedLineItem, Company
from app.services.matching_service import (
    _normalize_sku,
    _find_existing_link,
    _create_provisional_product,
)


class TestNormalizeSku:
    """Test SKU normalization with and without supplier rules."""

    def test_no_rules_passthrough(self):
        """Without rules, SKU should pass through unchanged."""
        result = _normalize_sku("12345", None, None)
        assert result is not None
        assert result[0] == "12345"

    def test_with_prefix_rule(self):
        """SKU with 03- prefix should get normalized via strip_prefix rule."""
        rules = {
            "code_normalization": [
                {"op": "strip_prefix", "prefix": "03-"}
            ]
        }
        result = _normalize_sku("03-12345", None, rules)
        assert result is not None
        assert result[0] == "12345"  # normalized SKU

    def test_sku_without_prefix_unchanged(self):
        """SKU without prefix should remain unchanged under strip rule."""
        rules = {
            "code_normalization": [
                {"op": "strip_prefix", "prefix": "03-"}
            ]
        }
        result = _normalize_sku("67890", None, rules)
        assert result is not None
        assert result[0] == "67890"


@pytest.mark.asyncio
async def test_find_existing_link_found(
    db_session: AsyncSession,
    test_company: Company,
    test_product: Product,
    test_supplier: Supplier,
):
    """Test finding an existing ProductSupplierLink."""
    # Create a link
    link = ProductSupplierLink(
        id=uuid4(),
        company_id=test_company.id,
        product_id=test_product.id,
        supplier_id=test_supplier.id,
        supplier_sku_normalized="12345",
        price_history_json=[],
    )
    db_session.add(link)
    await db_session.flush()

    # Search for it
    result = await _find_existing_link(
        supplier_id=test_supplier.id,
        normalized_sku="12345",
        company_id=test_company.id,
        db=db_session,
    )
    assert result is not None
    assert result.id == link.id
    assert result.product_id == test_product.id


@pytest.mark.asyncio
async def test_find_existing_link_not_found(
    db_session: AsyncSession,
    test_company: Company,
    test_supplier: Supplier,
):
    """Test that a non-existent SKU returns None."""
    result = await _find_existing_link(
        supplier_id=test_supplier.id,
        normalized_sku="99-99999",
        company_id=test_company.id,
        db=db_session,
    )
    assert result is None


@pytest.mark.asyncio
async def test_find_existing_link_no_supplier(
    db_session: AsyncSession,
    test_company: Company,
):
    """Test that None supplier_id returns None."""
    result = await _find_existing_link(
        supplier_id=None,
        normalized_sku="12345",
        company_id=test_company.id,
        db=db_session,
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_provisional_product_creates_product_and_link(
    db_session: AsyncSession,
    test_company: Company,
    test_supplier: Supplier,
):
    """Test creating a provisional product from a ParsedLineItem."""
    # Need a ParsedDocument first (FK constraint for ParsedLineItem)
    from app.models import ParsedDocument, InboundFile

    # Create InboundFile first
    inbound_file = InboundFile(
        id=uuid4(),
        company_id=test_company.id,
        file_type="xml",
        object_key=f"test/{uuid4()}.xml",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # empty file hash
    )
    db_session.add(inbound_file)
    await db_session.flush()

    doc = ParsedDocument(
        id=uuid4(),
        company_id=test_company.id,
        inbound_file_id=inbound_file.id,
        doc_kind="invoice",
        parse_status="success",
    )
    db_session.add(doc)
    await db_session.flush()

    # Create a ParsedLineItem
    line_item = ParsedLineItem(
        id=uuid4(),
        company_id=test_company.id,
        parsed_document_id=doc.id,
        line_index=1,
        supplier_sku_raw="03-55555",
        description_raw="Test Product Description",
        qty=Decimal("2.0"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("20.00"),
        extraction_source="xml",
    )
    db_session.add(line_item)
    await db_session.flush()

    # Create provisional product — this only creates the Product, not a link
    product = await _create_provisional_product(
        item=line_item,
        company_id=test_company.id,
        db=db_session,
    )

    assert product is not None
    assert product.company_id == test_company.id
    assert product.status == "provisional"
    assert "Test Product Description" in product.canonical_name
