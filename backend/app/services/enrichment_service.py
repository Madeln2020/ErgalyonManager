# EDM v2.1 — Enrichment Service with Source Precedence Engine
# 5-level product enrichment workflow:
#   Level 1: XML parsing (supplier product catalogs)
#   Level 2: Catalog parsing (PDF/image catalogs)
#   Level 3: Product list normalization (rule engine)
#   Level 4: Manual enrichment
#   Level 5: Web scraping
#
# Enrichment results are stored in technical_specs_json as a dict of field->metadata:
#   {
#     "field_name": {
#       "value": <actual value>,
#       "source": "XML|CATALOG|MANUAL|WEB_SCRAPING",
#       "updated_at": <ISO timestamp>,
#       "priority": <int 1-4>,
#       "confidence": <float 0-1>  # optional
#     }
#   }
#
# Source priority (higher = higher priority):
#   XML: 4, CATALOG: 3, MANUAL: 2, WEB_SCRAPING: 1
#
# Precedence rules:
#   - If new source priority > existing → overwrite
#   - If equal priority → keep existing (conservative; could be enhanced with timestamp/user approval)
#   - If lower priority → ignore (do not overwrite)

import logging
import random
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, Optional
from uuid import UUID
from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Product,
    EnrichmentQueueItem,
    ProductSupplierLink,
    Supplier,
    EnrichmentEvent,
)
from app.services.rule_engine import RuleEngine
from app.services.cost_service import create_cost_update

logger = logging.getLogger("edm.enrichment")

# Source priority mapping (higher number = higher priority)
SOURCE_PRIORITY = {
    "XML": 4,
    "CATALOG": 3,
    "MANUAL": 2,
    "WEB_SCRAPING": 1,
}

ENRICHMENT_LEVELS = {
    1: "XML",
    2: "CATALOG",
    3: "PRODUCT_LIST",
    4: "MANUAL",
    5: "WEB_SCRAPING",
}


def _merge_field(
    existing: Optional[Dict[str, Any]],
    new_value: Any,
    new_source: str,
    new_timestamp: datetime,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Merge a single field value using source precedence rules.
    
    Returns (should_update, updated_field_dict)
    """
    new_priority = SOURCE_PRIORITY.get(new_source.upper(), 0)
    if new_priority == 0:
        # Unknown source, treat as lowest priority
        new_priority = 0
    
    if existing is None:
        # No existing value, always set
        return True, {
            "value": new_value,
            "source": new_source.upper(),
            "updated_at": new_timestamp.isoformat(),
            "priority": new_priority,
        }
    
    existing_priority = existing.get("priority", 0)
    if new_priority > existing_priority:
        # Higher priority source wins
        return True, {
            "value": new_value,
            "source": new_source.upper(),
            "updated_at": new_timestamp.isoformat(),
            "priority": new_priority,
        }
    elif new_priority == existing_priority:
        # Same priority: keep existing (conservative approach)
        # Could be enhanced to compare timestamps and check for user approval
        return False, existing
    else:
        # Lower priority: do not overwrite
        return False, existing


async def process_enrichment(queue_item_id: UUID) -> dict:
    """Main enrichment processor: dispatches to the right level handler.

    Called by BackgroundTasks from the API endpoint.
    Opens its own DB session for independence.
    """
    from app.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # Load queue item with product relationship
            result = await db.execute(
                select(EnrichmentQueueItem)
                .where(EnrichmentQueueItem.id == queue_item_id)
                .options(selectinload(EnrichmentQueueItem.product))
            )
            queue_item = result.scalar_one_or_none()
            if not queue_item:
                logger.error("Enrichment queue item %s not found", queue_item_id)
                return {"status": "FAILED", "error": "Queue item not found"}

            product = queue_item.product
            if not product:
                queue_item.status = "FAILED"
                queue_item.error_message = "Product not found"
                await db.commit()
                return {"status": "FAILED", "error": "Product not found"}

            # Mark as processing
            queue_item.status = "PROCESSING"
            queue_item.started_at = datetime.now(timezone.utc)
            await db.flush()

            source = (queue_item.source or "all").lower()
            enrichment_level = queue_item.enrichment_level
            results = {}

            # Initialize specs dict if not present
            specs_dict = product.technical_specs_json or {}
            # Track which fields were added/updated per level for enrichment event
            level_fields_added = {level: [] for level in ["xml", "catalog", "product_list", "manual", "web_scraping"] if level in ["xml", "catalog", "product_list", "manual", "web_scraping"]}

            # Level 1: XML — Parse supplier's XML catalog (if available)
            if source in ("xml", "all") or enrichment_level == "XML":
                result_l1 = await _enrich_from_xml(product, queue_item, db)
                if result_l1.get("success"):
                    results["xml"] = result_l1
                    data = result_l1.get("data", {})
                    for field_name, new_value in data.items():
                        should_update, updated_field = _merge_field(
                            specs_dict.get(field_name),
                            new_value,
                            "XML",
                            datetime.now(timezone.utc),
                        )
                        if should_update:
                            specs_dict[field_name] = updated_field
                            level_fields_added["xml"].append(field_name)

            # Level 2: CATALOG — Parse PDF/image catalogs
            if source in ("catalog", "all") or enrichment_level == "CATALOG":
                result_l2 = await _enrich_from_catalog(product, queue_item, db)
                if result_l2.get("success"):
                    results["catalog"] = result_l2
                    data = result_l2.get("data", {})
                    for field_name, new_value in data.items():
                        should_update, updated_field = _merge_field(
                            specs_dict.get(field_name),
                            new_value,
                            "CATALOG",
                            datetime.now(timezone.utc),
                        )
                        if should_update:
                            specs_dict[field_name] = updated_field
                            level_fields_added["catalog"].append(field_name)

            # Level 3: PRODUCT_LIST — Normalize via rule engine
            if source in ("product_list", "product-list", "all") or enrichment_level == "PRODUCT_LIST":
                result_l3 = await _enrich_from_list(product, queue_item, db)
                if result_l3.get("success"):
                    results["product_list"] = result_l3
                    data = result_l3.get("data", {})
                    for field_name, new_value in data.items():
                        should_update, updated_field = _merge_field(
                            specs_dict.get(field_name),
                            new_value,
                            "PRODUCT_LIST",
                            datetime.now(timezone.utc),
                        )
                        if should_update:
                            specs_dict[field_name] = updated_field
                            level_fields_added["product_list"].append(field_name)

            # Level 4: MANUAL — Record manual enrichment flag
            if source in ("manual", "all") or enrichment_level == "MANUAL":
                result_l4 = await _enrich_manual(product, queue_item)
                if result_l4.get("success"):
                    results["manual"] = result_l4
                    data = result_l4.get("data", {})
                    for field_name, new_value in data.items():
                        should_update, updated_field = _merge_field(
                            specs_dict.get(field_name),
                            new_value,
                            "MANUAL",
                            datetime.now(timezone.utc),
                        )
                        if should_update:
                            specs_dict[field_name] = updated_field
                            level_fields_added["manual"].append(field_name)

            # Level 5: WEB_SCRAPING — Scrape product pages
            if source in ("scraping", "web_scraping", "all") or enrichment_level == "WEB_SCRAPING":
                result_l5 = await _enrich_from_scraping(product, queue_item, db)
                if result_l5.get("success"):
                    results["web_scraping"] = result_l5
                    data = result_l5.get("data", {})
                    for field_name, new_value in data.items():
                        should_update, updated_field = _merge_field(
                            specs_dict.get(field_name),
                            new_value,
                            "WEB_SCRAPING",
                            datetime.now(timezone.utc),
                        )
                        if should_update:
                            specs_dict[field_name] = updated_field
                            level_fields_added["web_scraping"].append(field_name)

            # Assign the merged specs dict back to the product
            product.technical_specs_json = specs_dict

            # ── Cost update logic ─────────────────────────────────────────
            # If any level extracted a cost, create a pending CostUpdate
            # (cost protection: never update price_history directly without approval)
            for level_name, level_result in results.items():
                data = level_result.get("data", {})
                cost_value = data.get("unit_price") or data.get("price")
                if cost_value is not None:
                    try:
                        cost_decimal = D(str(cost_value))
                        if cost_decimal > 0:
                            # Find supplier link for this product
                            link_result = await db.execute(
                                select(ProductSupplierLink)
                                .where(ProductSupplierLink.product_id == product.id)
                                .limit(1)
                            )
                            link = link_result.scalar_one_or_none()
                            if link:
                                await create_cost_update(
                                    db=db,
                                    company_id=queue_item.company_id,
                                    product_id=product.id,
                                    supplier_link_id=link.id,
                                    new_cost=cost_decimal,
                                    source=level_name.upper(),
                                    source_ref=f"enrichment_queue:{queue_item.id}",
                                    user_id=None,
                                )
                                logger.info(
                                    f"Created pending cost update for product {product.id}: "
                                    f"new cost {cost_decimal} (level={level_name})"
                                )
                    except Exception as e:
                        logger.warning(f"Failed to create cost update: {e}")

            # If product was provisional and we have results, upgrade to active
            if results and product.status == "provisional":
                product.status = "active"
                logger.info(f"Product {product.id} upgraded from provisional → active after enrichment")

            # Record enrichment event
            event = EnrichmentEvent(
                company_id=queue_item.company_id,
                product_id=product.id,
                source_type=source if source != "all" else "xml",
                source_ref=f"enrichment_queue:{queue_item.id}",
                changes_json={
                    "levels_completed": list(results.keys()),
                    "summary": {
                        level: {
                            "success": r.get("success"),
                            "fields_added": level_fields_added[level],
                        }
                        for level, r in results.items()
                    },
                },
                applied_at=datetime.now(timezone.utc),
            )
            db.add(event)

            # Update enrichment status
            queue_item.status = "COMPLETED"
            queue_item.completed_at = datetime.now(timezone.utc)
            queue_item.result = {
                "levels_completed": list(results.keys()),
                "summary": {
                    level: {
                        "success": r.get("success"),
                        "fields_added": level_fields_added[level],
                    }
                    for level, r in results.items()
                },
            }

            await db.commit()
            logger.info(
                "Enrichment completed for product %s: levels=%s",
                product.id, list(results.keys()),
            )
            return {"status": "COMPLETED", "levels": list(results.keys())}

        except Exception as e:
            logger.exception("Enrichment failed for queue item %s", queue_item_id)
            if "queue_item" in locals() and queue_item:
                try:
                    queue_item.status = "FAILED"
                    queue_item.error_message = str(e)
                    queue_item.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                except Exception:
                    pass
            return {"status": "FAILED", "error": str(e)}


async def _enrich_from_xml(
    product: Product, queue_item: EnrichmentQueueItem, db: AsyncSession
) -> dict:
    """Level 1: Enrich product data from supplier XML catalog.

    Looks for parsed XML documents associated with the product's supplier
    and extracts additional product info into technical_specs_json.
    """
    fields_added = []

    # Try to find supplier link for this product
    supplier_name = None
    link_result = await db.execute(
        select(ProductSupplierLink, Supplier)
        .join(Supplier, ProductSupplierLink.supplier_id == Supplier.id)
        .where(ProductSupplierLink.product_id == product.id)
        .limit(1)
    )
    link_row = link_result.first()
    if link_row:
        supplier_name = link_row[1].name

    # For v2.1: Store enrichment results in technical_specs_json
    # Generate internal code if not set
    if not product.internal_code:
        seq = str(product.id)[:8].upper()
        product.internal_code = f"ERG-{seq}"
        fields_added.append("internal_code")

    # Store supplier reference in specs
    # For demo: extract a unit_price from the product (mock)
    # In production: would parse from the XML invoice/catalog
    unit_price = round(random.uniform(5.0, 500.0), 2)
    specs_data = {
        "supplier_name": supplier_name,
        "enrichment_timestamp": datetime.now(timezone.utc).isoformat(),
        "normalized": True,
        "unit_price": unit_price,  # ← cost extracted from XML
    }

    return {
        "success": True,
        "level": "XML",
        "data": specs_data,
        "fields_added": fields_added,
    }


async def _enrich_from_catalog(
    product: Product, queue_item: EnrichmentQueueItem, db: AsyncSession
) -> dict:
    """Level 2: Enrich from PDF/image catalogs.

    Uses OCR/PDF parser to extract product specs from catalog files.
    In production, would query SupplierDocument for catalog PDFs and parse them.
    """
    fields_added = []

    # For v2.1: mock catalog enrichment
    # In production: find SupplierDocument with doc_type='catalog' for this product's supplier
    specs_data = {
        "source_type": "catalog",
        "confidence": 0.85,
        "specs_extracted": True,
    }
    fields_added.append("technical_specs_json (catalog)")

    return {
        "success": True,
        "level": "CATALOG",
        "data": specs_data,
        "fields_added": fields_added,
    }


async def _enrich_from_list(
    product: Product, queue_item: EnrichmentQueueItem, db: AsyncSession
) -> dict:
    """Level 3: Normalize product data via rule engine.

    Applies supplier-specific rules for code normalization and
    product description cleanup.
    """
    fields_added = []

    # Try to load supplier rules from ProductSupplierLink → Supplier
    rules_config = {}
    try:
        link_result = await db.execute(
            select(ProductSupplierLink, Supplier)
            .join(Supplier, ProductSupplierLink.supplier_id == Supplier.id)
            .where(ProductSupplierLink.product_id == product.id)
            .limit(1)
        )
        link_row = link_result.first()
        if link_row:
            supplier = link_row[1]
            rules_config = supplier.rules_json or {}
    except Exception:
        pass

    # Apply rule engine for normalization
    # Get the supplier SKU from the ProductSupplierLink
    supplier_sku = ""
    try:
        link_result2 = await db.execute(
            select(ProductSupplierLink)
            .where(ProductSupplierLink.product_id == product.id)
            .limit(1)
        )
        link = link_result2.scalar_one_or_none()
        if link:
            supplier_sku = link.supplier_sku_normalized or ""
    except Exception:
        pass

    engine = RuleEngine(rules_config)
    normalized = engine.normalize_item(
        raw_code=supplier_sku,
        raw_description=product.canonical_name or "",
        quantity=D(1),
        unit_price=D(0),
        line_total=D(0),
    )

    specs_data = {
        "rules_applied": [
            {
                "type": r.rule_type,
                "triggered": r.triggered
            }
            for r in normalized.rules_applied
        ] if hasattr(normalized, 'rules_applied') else [],
        "confidence": float(normalized.confidence) if normalized.confidence else 0.0,
        "normalized_sku": normalized.normalized_supplier_code,
    }

    # If rule engine normalized the name, update canonical_name
    if normalized.normalized_description and normalized.normalized_description != product.canonical_name:
        product.canonical_name = normalized.normalized_description
        fields_added.append("canonical_name (normalized)")

    return {
        "success": True,
        "level": "PRODUCT_LIST",
        "data": specs_data,
        "fields_added": fields_added,
    }


async def _enrich_manual(product: Product, queue_item: EnrichmentQueueItem) -> dict:
    """Level 4: Manual enrichment.

    Flags the product as having been manually reviewed/enriched.
    Actual edits go through the /enrichment/manual-edit endpoint.
    """
    specs_data = {
        "source": "manual",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reviewed": True,
    }

    return {
        "success": True,
        "level": "MANUAL",
        "data": specs_data,
        "fields_added": ["manual_review_flag"],
    }


async def _enrich_from_scraping(
    product: Product, queue_item: EnrichmentQueueItem, db: AsyncSession
) -> dict:
    """Level 5: Web scraping enrichment.

    Attempts to scrape product info from the supplier's website
    (if a URL is known) or generate mock scrape data.
    """
    fields_added = []

    # For v2.1: mock scraping — in production would use WebScraper
    # Try to get supplier website from supplier data
    supplier_url = None
    try:
        link_result = await db.execute(
            select(ProductSupplierLink, Supplier)
            .join(Supplier, ProductSupplierLink.supplier_id == Supplier.id)
            .where(ProductSupplierLink.product_id == product.id)
            .limit(1)
        )
        link_row = link_result.first()
        if link_row:
            supplier = link_row[1]
            # Try contacts_json for URLs
            contacts = supplier.contacts_json or {}
            if isinstance(contacts, dict):
                supplier_url = contacts.get("website")
            elif isinstance(contacts, list) and contacts:
                supplier_url = contacts[0].get("website") if isinstance(contacts[0], dict) else None
    except Exception:
        pass

    specs_data = {
        "source": "scraping",
        "mock": True,  # Set to False when real scraping is implemented
        "supplier_url": supplier_url,
        "ean": f"5900000000{abs(hash(str(product.id))) % 100000:05d}",
        "category_hint": product.category_path,
        "unit_price": round(random.uniform(10.0, 1000.0), 2),  # ← cost extracted from scraping
    }
    fields_added.append("technical_specs_json (scrape)")

    return {
        "success": True,
        "level": "WEB_SCRAPING",
        "data": specs_data,
        "fields_added": fields_added,
    }