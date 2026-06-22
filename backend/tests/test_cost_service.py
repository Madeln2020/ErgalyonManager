"""
Unit tests for Cost Management Service — tests the actual functions.
"""
import pytest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CostUpdate, Product, ProductSupplierLink, Company
from app.services.cost_service import create_cost_update, approve_cost_update, reject_cost_update


@pytest.mark.asyncio
async def test_create_cost_update(
    db_session: AsyncSession,
    test_company: Company,
    test_product: Product,
    test_product_supplier_link: ProductSupplierLink,
):
    """Test creating a pending cost update."""
    # Fixtures already created and flushed entities — use them directly
    cost_update = await create_cost_update(
        db=db_session,
        company_id=test_company.id,
        product_id=test_product.id,
        supplier_link_id=test_product_supplier_link.id,
        new_cost=Decimal("29.99"),
        source="manual",
        notes="Test cost update",
        user_id=None,
    )

    assert cost_update.id is not None
    assert cost_update.status == "pending"
    assert cost_update.new_cost == Decimal("29.99")
    assert cost_update.old_cost is None  # No history yet
    assert cost_update.source == "manual"


@pytest.mark.asyncio
async def test_approve_cost_update(
    db_session: AsyncSession,
    test_company: Company,
    test_product: Product,
    test_product_supplier_link: ProductSupplierLink,
):
    """Test approving a pending cost update."""
    # Create pending cost update first
    cost_update = await create_cost_update(
        db=db_session,
        company_id=test_company.id,
        product_id=test_product.id,
        supplier_link_id=test_product_supplier_link.id,
        new_cost=Decimal("29.99"),
        source="manual",
        user_id=None,
    )
    assert cost_update.status == "pending"

    # Approve it
    approved = await approve_cost_update(
        db=db_session,
        cost_update_id=cost_update.id,
        approved_by=None,  # user_id can be None
    )

    assert approved.status == "approved"
    assert approved.approved_by is None
    assert approved.approved_at is not None

    # Verify history was updated on the link
    await db_session.refresh(test_product_supplier_link)
    assert test_product_supplier_link.price_history_json is not None
    if isinstance(test_product_supplier_link.price_history_json, list):
        assert len(test_product_supplier_link.price_history_json) > 0
        last_entry = test_product_supplier_link.price_history_json[-1]
        assert last_entry["cost"] == float(Decimal("29.99"))
        assert last_entry["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_cost_update(
    db_session: AsyncSession,
    test_company: Company,
    test_product: Product,
    test_product_supplier_link: ProductSupplierLink,
):
    """Test rejecting a pending cost update — history should NOT be updated."""
    cost_update = await create_cost_update(
        db=db_session,
        company_id=test_company.id,
        product_id=test_product.id,
        supplier_link_id=test_product_supplier_link.id,
        new_cost=Decimal("15.50"),
        source="invoice",
        user_id=None,
    )

    rejected = await reject_cost_update(
        db=db_session,
        cost_update_id=cost_update.id,
        rejected_by=None,  # user_id can be None
        reason="Duplicate entry",
    )

    assert rejected.status == "rejected"
    assert rejected.rejected_by is None
    assert rejected.rejected_at is not None

    # History should NOT have been updated (rejection doesn't modify history)
    await db_session.refresh(test_product_supplier_link)
    assert test_product_supplier_link.price_history_json == []


@pytest.mark.asyncio
async def test_cost_protection_prevents_overwrite_without_approval(
    db_session: AsyncSession,
    test_company: Company,
    test_product: Product,
    test_product_supplier_link: ProductSupplierLink,
):
    """Cost should NOT go to price_history until approved."""
    # Create a cost update
    cost_update = await create_cost_update(
        db=db_session,
        company_id=test_company.id,
        product_id=test_product.id,
        supplier_link_id=test_product_supplier_link.id,
        new_cost=Decimal("99.99"),
        source="manual",
        user_id=None,
    )

    # Before approval, the link's history should NOT contain this cost
    await db_session.refresh(test_product_supplier_link)
    history = test_product_supplier_link.price_history_json or []
    assert len(history) == 0  # Nothing in history yet

    # After approval, it should be there
    await approve_cost_update(
        db=db_session,
        cost_update_id=cost_update.id,
        approved_by=None,  # user_id can be None
    )
    await db_session.refresh(test_product_supplier_link)
    history = test_product_supplier_link.price_history_json or []
    assert len(history) == 1
    assert history[0]["cost"] == float(Decimal("99.99"))
