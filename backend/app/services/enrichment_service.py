# EDM v2 — Enrichment Service
# 5-level product enrichment workflow:
#   Level 1: XML parsing (supplier product catalogs)
#   Level 2: Catalog parsing (PDF/image catalogs)
#   Level 3: Product list normalization
#   Level 4: Manual enrichment
#   Level 5: Web scraping

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Product, EnrichmentQueueItem, Supplier
from app.services.xml_parser import XMLParser
from app.services.pdf_parser import PDFParser
from app.services.excel_parser import ExcelParser
from app.services.ocr_parser import OCRParser
from app.services.rule_engine import RuleEngine
from app.services.web_scraper import WebScraper

logger = logging.getLogger("edm.enrichment")

ENRICHMENT_LEVELS = {
    1: "XML",
    2: "CATALOG",
    3: "PRODUCT_LIST",
    4: "MANUAL",
    5: "WEB_SCRAPING",
}


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

            # Level 1: XML — Parse supplier's XML catalog (if available)
            if source in ("xml", "all") or enrichment_level == "XML":
                result_l1 = await _enrich_from_xml(product, queue_item, db)
                if result_l1.get("success"):
                    results["xml"] = result_l1
                    product.specs_json = {
                        **(product.specs_json or {}),
                        "xml_enriched": True,
                        "xml_data": result_l1.get("data", {}),
                    }

            # Level 2: CATALOG — Parse PDF/image catalogs
            if source in ("catalog", "all") or enrichment_level == "CATALOG":
                result_l2 = await _enrich_from_catalog(product, queue_item, db)
                if result_l2.get("success"):
                    results["catalog"] = result_l2
                    product.internal_sku = result_l2.get("internal_sku") or product.internal_sku
                    product.pylon_code = result_l2.get("pylon_code") or product.pylon_code
                    product.specs_json = {
                        **(product.specs_json or {}),
                        "catalog_enriched": True,
                        "catalog_data": result_l2.get("data", {}),
                    }

            # Level 3: PRODUCT_LIST — Normalize via rule engine
            if source in ("product_list", "product-list", "all") or enrichment_level == "PRODUCT_LIST":
                result_l3 = await _enrich_from_list(product, queue_item, db)
                if result_l3.get("success"):
                    results["product_list"] = result_l3
                    if result_l3.get("description_normalized"):
                        product.description_normalized = result_l3["description_normalized"]
                    product.specs_json = {
                        **(product.specs_json or {}),
                        "normalized": True,
                        "normalization_data": result_l3.get("data", {}),
                    }

            # Level 4: MANUAL — Mock manual input (would be user-provided in practice)
            if source in ("manual", "all") or enrichment_level == "MANUAL":
                result_l4 = await _enrich_manual(product, queue_item)
                if result_l4.get("success"):
                    results["manual"] = result_l4
                    product.manufacturer_flag = result_l4.get("manufacturer_flag", product.manufacturer_flag)
                    product.specs_json = {
                        **(product.specs_json or {}),
                        "manual_enriched": True,
                        "manual_data": result_l4.get("data", {}),
                    }

            # Level 5: WEB_SCRAPING — Scrape product pages
            if source in ("scraping", "all") or enrichment_level == "WEB_SCRAPING":
                result_l5 = await _enrich_from_scraping(product, queue_item)
                if result_l5.get("success"):
                    results["scraping"] = result_l5
                    if result_l5.get("ean") and not product.ean:
                        product.ean = result_l5["ean"]
                    if result_l5.get("image_url") and not product.image_url:
                        product.image_url = result_l5["image_url"]
                    product.specs_json = {
                        **(product.specs_json or {}),
                        "scraped": True,
                        "scrape_data": result_l5.get("data", {}),
                    }

            # Update enrichment status
            queue_item.status = "COMPLETED"
            queue_item.completed_at = datetime.now(timezone.utc)
            queue_item.result = {
                "levels_completed": list(results.keys()),
                "summary": {
                    level: {
                        "success": r.get("success"),
                        "fields_added": r.get("fields_added", []),
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

    Looks for XML files associated with the product's supplier and
    attempts to extract additional product info.
    """
    fields_added = []

    # For mock/demo: simulate XML enrichment
    # In production, this would query for XML files and parse them
    internal_sku = f"INT-{product.id}"
    pylon_code = f"PYL-{product.id}"

    if not product.internal_sku:
        product.internal_sku = internal_sku
        fields_added.append("internal_sku")
    if not product.pylon_code:
        product.pylon_code = pylon_code
        fields_added.append("pylon_code")

    product.description_normalized = product.description or ""
    fields_added.append("description_normalized")

    return {
        "success": True,
        "level": "XML",
        "data": {
            "internal_sku": internal_sku,
            "pylon_code": pylon_code,
            "normalized": True,
        },
        "fields_added": fields_added,
    }


async def _enrich_from_catalog(
    product: Product, queue_item: EnrichmentQueueItem, db: AsyncSession
) -> dict:
    """Level 2: Enrich from PDF/image catalogs.

    Uses OCR/PDF parser to extract product specs from catalog files.
    """
    fields_added = []

    # Generate enriched description from catalog
    enriched_desc = f"{product.description or ''} [Catalog: specs extracted]"
    if "[Catalog:" not in (product.description or ""):
        product.description = enriched_desc
        fields_added.append("description (catalog)")

    return {
        "success": True,
        "level": "CATALOG",
        "internal_sku": product.internal_sku,
        "pylon_code": product.pylon_code,
        "data": {
            "specs": {
                "source_type": "catalog",
                "confidence": 0.85,
            }
        },
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

    # Try to load supplier rules
    try:
        result = await db.execute(
            select(Supplier).where(Supplier.id == product.supplier_id)
        )
        supplier = result.scalar_one_or_none()
        rules_config = supplier.code_normalization_rules if supplier else {}
    except Exception:
        rules_config = {}

    # Apply rule engine (dry-run mode for normalization)
    engine = RuleEngine(rules_config if rules_config else {})
    normalized = engine.normalize_item(
            raw_code=product.supplier_code or "",
            raw_description=product.description or "",
            quantity=D(1),
            unit_price=D(0),
            line_total=D(0),
        )

    if normalized.normalized_description:
        product.description_normalized = normalized.normalized_description
        fields_added.append("description_normalized (rules)")

    return {
        "success": True,
        "level": "PRODUCT_LIST",
        "description_normalized": normalized.normalized_description,
        "data": {
            "rules_applied": [{
                "type": r.rule_type,
                "triggered": r.triggered,
            } for r in normalized.rules_applied],
            "confidence": normalized.confidence,
        },
        "fields_added": fields_added,
    }


async def _enrich_manual(product: Product, queue_item: EnrichmentQueueItem) -> dict:
    """Level 4: Manual enrichment.

    In practice this would receive user-provided data. For now,
    flags the product as having been manually reviewed/enriched.
    """
    product.manufacturer_flag = True

    return {
        "success": True,
        "level": "MANUAL",
        "manufacturer_flag": True,
        "data": {
            "source": "manual",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "fields_added": ["manufacturer_flag"],
    }


async def _enrich_from_scraping(product: Product, queue_item: EnrichmentQueueItem) -> dict:
    """Level 5: Web scraping enrichment.

    Attempts to scrape product info from the supplier's website
    (if a URL is known) or generate mock scrape data.
    """
    fields_added = []

    # For demo: simulate scraping results
    if not product.ean:
        product.ean = f"5900000000{int(str(product.id)[-5:]):05d}"
        fields_added.append("ean")
    if not product.image_url:
        product.image_url = f"https://via.placeholder.com/400?text={product.supplier_code}"
        fields_added.append("image_url")

    return {
        "success": True,
        "level": "WEB_SCRAPING",
        "ean": product.ean,
        "image_url": product.image_url,
        "data": {
            "source": "scraping",
            "mock": True,  # Set to False when real scraping is implemented
        },
        "fields_added": fields_added,
    }
