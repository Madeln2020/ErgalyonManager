# EDM v2.1 — Supplier Service
# CRUD operations for suppliers with AADE integration

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supplier, Company, User
from app.schemas import SupplierCreate, SupplierUpdate, SupplierListRead
from app.auth import get_current_user, require_role, Role
from app.services.aade_service import fetch_tax_profile_for_supplier
from app.services.audit_service import log_event

logger = logging.getLogger("edm.supplier")


async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession,
    current_user: User,
) -> Supplier:
    """Create a new supplier with optional AADE integration.

    If vat_number is provided, attempts to fetch tax profile from AADE.
    """
    # Check if vat_number is unique per company
    if data.vat_number:
        existing = await db.execute(
            select(Supplier).where(
                Supplier.company_id == data.company_id,
                Supplier.vat_number == data.vat_number,
                Supplier.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Supplier with this VAT number already exists in this company",
            )

    # Fetch AADE profile if vat_number provided
    tax_profile = None
    if data.vat_number:
        try:
            tax_profile = await fetch_tax_profile_for_supplier(data.vat_number)
        except Exception as exc:
            logger.warning(
                "Failed to fetch AADE profile for %s: %s",
                data.vat_number,
                exc,
                exc_info=True,
            )
            # Continue without AADE data - not critical

    # Create supplier
    supplier_data = data.model_dump()
    supplier_data["company_id"] = current_user.company_id
    supplier = Supplier(**supplier_data)

    # Add AADE profile if available
    if tax_profile:
        supplier.tax_profile_json = tax_profile

    db.add(supplier)
    await db.flush()
    await db.refresh(supplier)

    logger.info("Created supplier %s with VAT %s", supplier.id, supplier.vat_number)

    return supplier


async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> Optional[Supplier]:
    """Get a single supplier by ID."""
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.company_id == current_user.company_id,
            Supplier.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def list_suppliers(
    db: AsyncSession,
    current_user: User,
    *,
    is_active: Optional[bool] = None,
) -> list[Supplier]:
    """List suppliers for the current user's company."""
    query = select(Supplier).where(
        Supplier.company_id == current_user.company_id,
        Supplier.is_deleted == False,
    )

    if is_active is not None:
        query = query.where(Supplier.is_active == is_active)

    query = query.order_by(Supplier.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_supplier(
    supplier_id: UUID,
    data: SupplierUpdate,
    db: AsyncSession,
    current_user: User,
) -> Optional[Supplier]:
    """Update supplier with optional AADE integration for VAT changes."""
    supplier = await get_supplier(supplier_id, db, current_user)
    if not supplier:
        return None

    old_values = {field: getattr(supplier, field) for field in data.model_dump(exclude_unset=True)}

    # Check vat_number uniqueness if being updated
    if data.vat_number and data.vat_number != supplier.vat_number:
        existing = await db.execute(
            select(Supplier).where(
                Supplier.company_id == current_user.company_id,
                Supplier.vat_number == data.vat_number,
                Supplier.id != supplier_id,
                Supplier.is_deleted == False,
            )
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Supplier with this VAT number already exists in this company",
            )

        # Fetch new AADE profile if VAT is changing
        if data.vat_number:
            try:
                tax_profile = await fetch_tax_profile_for_supplier(data.vat_number)
                if tax_profile:
                    supplier.tax_profile_json = tax_profile
            except Exception as exc:
                logger.warning(
                    "Failed to fetch AADE profile for %s: %s",
                    data.vat_number,
                    exc,
                    exc_info=True,
                )

    # Update fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    await db.flush()
    await db.refresh(supplier)

    logger.info("Updated supplier %s", supplier.id)

    return supplier


async def delete_supplier(
    supplier_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> Optional[Supplier]:
    """Soft-delete a supplier."""
    supplier = await get_supplier(supplier_id, db, current_user)
    if not supplier:
        return None

    supplier.is_deleted = True
    supplier.is_active = False
    await db.flush()

    logger.info("Soft-deleted supplier %s", supplier_id)

    return supplier
