"""
EDM v2.1 — Product Matching Service

Takes parsed line items (from ParsedLineItem records), normalizes supplier SKUs
using the RuleEngine, matches against existing ProductSupplierLink records,
and creates MatchDecisions / new Products as needed.

Flow:
  1. Load supplier rules from DB → RuleEngine
  2. Normalize supplier_sku_raw → supplier_sku_normalized
  3. Search existing ProductSupplierLink by (supplier_id, normalized_sku)
  4a. Found → auto_exact match → create MatchDecision
  4b. Not found → search Products by description (candidates) → auto_suggested
  4c. No candidates → create new Product + ProductSupplierLink + auto_exact
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    Company,
    InboundFile,
    MatchDecision,
    ParsedDocument,
    ParsedLineItem,
    Product,
    ProductSupplierLink,
    Supplier,
)
from app.services.rule_engine import RuleEngine
from app.services.review_service import create_match_review_task

logger = logging.getLogger("edm.matching")


def _normalize_sku(raw_sku: str, supplier_id: Optional[UUID], db_supplier_rules: Optional[dict]) -> tuple[str, float, list]:
    """
    Normalize a supplier SKU using the RuleEngine.
    Returns (normalized_sku, confidence, rules_applied).
    Special case: Poimenidis 03- prefix strip (config-driven).
    """
    rules = db_supplier_rules or {}
    engine = RuleEngine(rules, supplier_id=str(supplier_id) if supplier_id else "unknown")
    norm = engine.normalize_item(
        raw_code=raw_sku,
        raw_description="",
        quantity=Decimal("1"),
        unit_price=Decimal("0"),
        line_total=Decimal("0"),
    )
    return norm.normalized_supplier_code, norm.confidence, [str(r) for r in norm.rules_applied]


async def match_line_item(
    item: ParsedLineItem,
    supplier_id: Optional[UUID],
    company_id: UUID,
    db: AsyncSession,
) -> Optional[MatchDecision]:
    """
    Match a single ParsedLineItem to a product.
     1. Normalize the SKU
     2. Look for existing ProductSupplierLink
     3. If found → auto_exact MatchDecision
     4. If not → search candidates by description → auto_suggested
     5. If no candidates → create provisional product → auto_exact

    Returns the created MatchDecision, or None if the item couldn't be matched.
    """
    # --- Step 1: Load supplier rules ---
    supplier_rules = None
    if supplier_id:
        result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
        supp = result.scalar_one_or_none()
        if supp and supp.rules_json:
            supplier_rules = supp.rules_json

    # --- Step 2: Normalize SKU ---
    raw_sku = item.supplier_sku_raw or ""
    normalized_sku, confidence, rules_list = _normalize_sku(raw_sku, supplier_id, supplier_rules)

    # Update the ParsedLineItem with normalized data
    item.supplier_sku_normalized = normalized_sku
    if item.description_raw:
        item.description_normalized = item.description_raw.strip()
    db.add(item)
    await db.flush()

    # --- Step 3: Look for existing ProductSupplierLink ---
    existing_link = await _find_existing_link(supplier_id, normalized_sku, company_id, db)

    if existing_link:
        # --- 3a: auto_exact match ---
        logger.info(f"Auto-exact match: SKU '{normalized_sku}' → Product {existing_link.product_id}")
        decision = MatchDecision(
            company_id=company_id,
            parsed_line_item_id=item.id,
            product_id=existing_link.product_id,
            product_supplier_link_id=existing_link.id,
            decision_type="auto_exact",
        )
        db.add(decision)
        await db.flush()
        return decision

    # --- Step 4: Search candidates by description ---
    candidates = await _find_candidates_by_description(item, supplier_id, company_id, db)

    if candidates:
        # --- 4b: auto_suggested — multiple candidates found ---
        logger.info(f"Auto-suggested: SKU '{normalized_sku}' → {len(candidates)} candidates")
        decision = MatchDecision(
            company_id=company_id,
            parsed_line_item_id=item.id,
            decision_type="auto_suggested",
            candidates_json=[{"product_id": str(p.id), "name": p.canonical_name} for p in candidates],
        )
        db.add(decision)
        await db.flush()
        # Create a review task for auto-suggested decisions
        if decision.decision_type == "auto_suggested":
            try:
                await create_match_review_task(
                    session=db,
                    company_id=company_id,
                    md_id=decision.id,
                    candidate_json=decision.candidates_json,
                )
                logger.info(f"Created review task for auto-suggested decision {decision.id}")
            except Exception as exc:
                logger.warning(f"Failed to create review task for {decision.id}: {exc}")
        return decision

    # --- Step 5: No candidates — create provisional product ---
    new_product = await _create_provisional_product(item, company_id, db)
    new_link = await _create_supplier_link(new_product, supplier_id, normalized_sku, raw_sku, company_id, db)

    logger.info(f"Created provisional product: {new_product.canonical_name} (SKU: {normalized_sku})")
    decision = MatchDecision(
        company_id=company_id,
        parsed_line_item_id=item.id,
        product_id=new_product.id,
        product_supplier_link_id=new_link.id,
        decision_type="auto_exact",
    )
    db.add(decision)
    await db.flush()
    return decision


async def match_parsed_document(
    parsed_doc_id: UUID,
    company_id: UUID,
    db: AsyncSession,
) -> int:
    """
    Match all line items in a ParsedDocument.
    Returns the number of items processed.
    """
    result = await db.execute(
        select(ParsedLineItem)
        .where(ParsedLineItem.parsed_document_id == parsed_doc_id)
        .order_by(ParsedLineItem.line_index)
    )
    items = result.scalars().all()

    # Load the parsed doc to get supplier_id via InboundFile
    doc_result = await db.execute(select(ParsedDocument).where(ParsedDocument.id == parsed_doc_id))
    doc = doc_result.scalar_one_or_none()
    supplier_id = None
    if doc:
        # Get supplier from the associated InboundFile
        file_result = await db.execute(
            select(InboundFile).where(InboundFile.id == doc.inbound_file_id)
        )
        inbound_file = file_result.scalar_one_or_none()
        if inbound_file:
            supplier_id = inbound_file.supplier_id

    matched = 0
    product_ids_to_enrich = []
    for item in items:
        decision = await match_line_item(item, supplier_id, company_id, db)
        if decision:
            matched += 1
            # Collect product IDs for enrichment (only for auto_exact with new products)
            if decision.product_id and decision.decision_type == "auto_exact":
                product_ids_to_enrich.append(decision.product_id)

    await db.commit()

    # Auto-trigger enrichment for newly matched products
    if product_ids_to_enrich:
        await _auto_trigger_enrichment(product_ids_to_enrich, company_id, db)

    return matched


async def _find_existing_link(
    supplier_id: Optional[UUID],
    normalized_sku: str,
    company_id: UUID,
    db: AsyncSession,
) -> Optional[ProductSupplierLink]:
    """Find an existing ProductSupplierLink by supplier + normalized SKU."""
    if not supplier_id or not normalized_sku:
        return None

    result = await db.execute(
        select(ProductSupplierLink).where(
            ProductSupplierLink.supplier_id == supplier_id,
            ProductSupplierLink.supplier_sku_normalized == normalized_sku,
            ProductSupplierLink.company_id == company_id,
        )
    )
    return result.scalar_one_or_none()


async def _find_candidates_by_description(
    item: ParsedLineItem,
    supplier_id: Optional[UUID],
    company_id: UUID,
    db: AsyncSession,
) -> list[Product]:
    """Find existing products with similar names/descriptions."""
    desc = (item.description_raw or "").strip()
    if not desc or len(desc) < 3:
        return []

    # Simple word-based matching: search for products with similar names
    words = [w for w in desc.lower().split() if len(w) > 2]
    if not words:
        return []

    # Build a query that matches any significant word in the description
    # Limit to 10 candidates
    conditions = []
    for w in words[:5]:  # first 5 words
        conditions.append(Product.canonical_name.ilike(f"%{w}%"))

    if not conditions:
        return []

    result = await db.execute(
        select(Product)
        .where(
            Product.company_id == company_id,
            or_(*conditions),
            Product.status.in_(["active", "provisional"]),
        )
        .limit(10)
    )
    candidates = result.scalars().all()

    # If supplier_id is set, prefer products already linked to this supplier
    if supplier_id and candidates:
        # Get product IDs that have a link to this supplier
        link_result = await db.execute(
            select(ProductSupplierLink.product_id)
            .where(
                ProductSupplierLink.supplier_id == supplier_id,
                ProductSupplierLink.product_id.in_([c.id for c in candidates]),
            )
        )
        linked_ids = {row[0] for row in link_result.fetchall()}
        # Sort: linked ones first
        candidates.sort(key=lambda p: (0 if p.id in linked_ids else 1))
        return candidates

    return candidates


async def _create_provisional_product(
    item: ParsedLineItem,
    company_id: UUID,
    db: AsyncSession,
) -> Product:
    """Create a new provisional product from a parsed line item."""
    # Generate internal code
    from app.database import async_session_factory
    from sqlalchemy import func

    # Count existing products to generate a sequential code
    count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.company_id == company_id)
    )
    count = count_result.scalar() or 0
    code_format = getattr(settings, "ERGALYON_CODE_FORMAT", "ERG-{seq:08d}")
    internal_code = code_format.format(seq=count + 1)

    name = (item.description_raw or "").strip() or f"Product {internal_code}"
    if len(name) > 500:
        name = name[:497] + "..."

    product = Product(
        company_id=company_id,
        canonical_name=name,
        internal_code=internal_code,
        status="provisional",
    )
    db.add(product)
    await db.flush()
    return product


async def _create_supplier_link(
    product: Product,
    supplier_id: Optional[UUID],
    normalized_sku: str,
    raw_sku: str,
    company_id: UUID,
    db: AsyncSession,
) -> ProductSupplierLink:
    """Create ProductSupplierLink for a newly matched product."""
    effective_sku = normalized_sku or raw_sku or "unknown"
    # If no supplier, create a generic link (will need manual assignment later)
    link_supplier_id = supplier_id  # can be None — DB allows nullable?
    # Actually supplier_id is NOT NULL in DB, so we need one.
    # Fallback: load the first supplier for this company
    if not link_supplier_id:
        from app.models import Supplier as SupplierModel
        supplier_result = await db.execute(
            select(SupplierModel)
            .where(SupplierModel.company_id == company_id)
            .limit(1)
        )
        first_supplier = supplier_result.scalar_one_or_none()
        if first_supplier:
            link_supplier_id = first_supplier.id
        else:
            # Last resort — use a sentinel UUID (shouldn't happen in practice)
            logger.warning(f"No supplier found for company {company_id}, using self-link")
            link_supplier_id = company_id  # as sentinel

    link = ProductSupplierLink(
        company_id=company_id,
        product_id=product.id,
        supplier_id=link_supplier_id,
        supplier_sku_normalized=effective_sku,
        supplier_sku_raw_examples=[raw_sku] if raw_sku else [],
    )
    db.add(link)
    await db.flush()
    return link


async def _auto_trigger_enrichment(
    product_ids: list,
    company_id: UUID,
    db: AsyncSession,
) -> None:
    """Auto-create enrichment queue items for newly matched products.

    Only creates items for products that don't already have a PENDING queue item.
    Enrichment runs via BackgroundTasks (called from the matching trigger endpoint).
    """
    from app.models import EnrichmentQueueItem

    for product_id in product_ids:
        # Skip if already has a PENDING item
        existing = await db.execute(
            select(EnrichmentQueueItem).where(
                EnrichmentQueueItem.product_id == product_id,
                EnrichmentQueueItem.status.in_(["PENDING", "PROCESSING"]),
            )
        )
        if existing.scalar_one_or_none():
            continue

        queue_item = EnrichmentQueueItem(
            company_id=company_id,
            product_id=product_id,
            source="all",
            enrichment_level=None,  # Run all levels
            status="PENDING",
        )
        db.add(queue_item)
        logger.info(f"Auto-created enrichment queue item for product {product_id}")

    await db.flush()
