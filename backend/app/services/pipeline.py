# EDM v2 — Processing Pipeline Service
# Φάση 1: upload → parse → normalize → product → review

import logging
from datetime import datetime
import os
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Invoice,
    InvoiceItem,
    Product,
    ReviewQueueItem,
    Supplier,
    PriceHistory,
)
from app.services.rule_engine import RuleEngine
from app.services.xml_parser import XMLParser
from app.services.pdf_parser import PDFParser
from app.services.excel_parser import ExcelParser
from app.services.ocr_parser import OCRParser

async def _process_image(invoice: Invoice, content: bytes, db: AsyncSession) -> dict:
    """Parse image using OCRParser."""
    filename = os.path.basename(invoice.file_path)
    parser = OCRParser(content, filename)
    parsed_list = parser.parse_all()
    if not parsed_list:
        raise ValueError("No invoices found in image (OCR)")
    parsed = parsed_list[0]
    items_created = 0
    total_net = Decimal("0")
    for idx, line in enumerate(parsed["lines"], start=1):
        item = InvoiceItem(
            invoice_id=invoice.id,
            line_number=idx,
            raw_supplier_code=line["supplier_code"],
            raw_description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_total=line["line_total"],
        )
        db.add(item)
        items_created += 1
        total_net += line["line_total"]
    return {
        "confidence": parsed.get("confidence", 100.0),
        "total_net": total_net,
        "items_created": items_created,
    }


logger = logging.getLogger(__name__)

# Precedence values (§1.4 P4)
SOURCE_PRECEDENCE = {
    "manual": 1,
    "xml": 2,
    "catalog": 3,
    "scraping": 4,
}


async def process_invoice_file(
    invoice: Invoice,
    file_content: bytes,
    db: AsyncSession,
) -> None:
    """
    Main processing pipeline for an uploaded invoice file.
    Steps: parse → normalize → match/create products → check review triggers.
    """
    invoice.status = "parsing"
    await db.flush()

    try:
        parsed = await _process_file(invoice, file_content, db)
        invoice.parsing_confidence = parsed.get("confidence", 100.0)
        invoice.total_amount = parsed.get("total_net")
        invoice.processed_at = datetime.now()
        invoice.status = "parsed"
        await db.flush()

        # Step 2: Apply supplier rules to normalize codes
        await _normalize_invoice(invoice, db)

        # Step 3: Create/update products from items
        await _process_products(invoice, db)

        # Step 4: Check review triggers
        await _check_review_triggers(invoice, db)

        invoice.status = "enriched"
        await db.flush()
        logger.info(f"Invoice {invoice.id} processed successfully")

    except Exception as e:
        invoice.status = "failed"
        invoice.error_message = str(e)
        await db.flush()
        logger.error(f"Invoice {invoice.id} processing failed: {e}")
        raise


async def _process_xml(
    invoice: Invoice, content: bytes, db: AsyncSession
) -> dict:
    """Parse XML and create InvoiceItems."""
    parser = XMLParser(content)
    parsed_invoices = parser.parse_all()

    if not parsed_invoices:
        raise ValueError("No invoices found in XML")

    items_created = 0
    total_net = Decimal("0")

    parsed = parsed_invoices[0]  # First invoice in document

    for line in parsed.lines:
        item = InvoiceItem(
            invoice_id=invoice.id,
            line_number=line.line_number,
            raw_supplier_code=line.supplier_code,
            raw_description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            line_total=line.line_total,
        )
        db.add(item)
        items_created += 1
        total_net += line.line_total

    return {
        "confidence": parsed.parsing_confidence,
        "total_net": total_net,
        "items_created": items_created,
    }


async def _normalize_invoice(invoice: Invoice, db: AsyncSession) -> None:
    """Apply supplier rules to normalize all item codes."""
    # Load supplier rules
    result = await db.execute(
        select(Supplier).where(Supplier.id == invoice.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        return

    rules_config = supplier.rules_json or {}
    engine = RuleEngine(rules_config, str(supplier.id))

    # Get all items for this invoice
    result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = result.scalars().all()

    for item in items:
        norm = engine.normalize_item(
            raw_code=item.raw_supplier_code or "",
            raw_description=item.raw_description,
            quantity=item.quantity or Decimal("1"),
            unit_price=item.unit_price or Decimal("0"),
            line_total=item.line_total or Decimal("0"),
        )
        item.normalized_supplier_code = norm.normalized_supplier_code
        item.match_confidence = Decimal(str(norm.confidence))


async def _process_products(invoice: Invoice, db: AsyncSession) -> None:
    """Match items to existing products or create new ones."""
    result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = result.scalars().all()

    for item in items:
        code = item.normalized_supplier_code or item.raw_supplier_code
        if not code:
            continue

        # Try to find existing product by supplier_code + supplier
        result = await db.execute(
            select(Product).where(
                Product.supplier_id == invoice.supplier_id,
                Product.supplier_code == code,
                Product.is_deleted == False,
            )
        )
        product = result.scalar_one_or_none()

        if product:
            # Update existing: price, description (with precedence check)
            product.current_price = item.unit_price
            if not product.description:
                product.description = item.raw_description
                product.description_normalized = item.raw_description
        else:
            # Create new product with auto-generated Ergalyon code
            product = Product(
                supplier_id=invoice.supplier_id,
                supplier_code=code,
                description=item.raw_description,
                description_normalized=item.raw_description,
                current_price=item.unit_price,
                price_currency="EUR",
                ergalyon_code=await _generate_ergalyon_code(db),
            )
            db.add(product)
            await db.flush()

        # Link invoice item to product
        item.product_id = product.id

        # Add price history
        ph = PriceHistory(
            product_id=product.id,
            price=item.unit_price or Decimal("0"),
            currency="EUR",
            supplier_id=invoice.supplier_id,
            invoice_id=invoice.id,
        )
        db.add(ph)


async def _check_review_triggers(invoice: Invoice, db: AsyncSession) -> None:
    """Check all review trigger conditions (§7.1)."""
    result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = result.scalars().all()

    for item in items:
        if not item.product_id:
            continue

        # Load product
        prod_result = await db.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            continue

        # 1. Missing manufacturer code → HIGH priority review
        if not product.manufacturer_code and not product.manufacturer_flag:
            # Δημιουργία review item με το mandatory prompt
            review = ReviewQueueItem(
                product_id=product.id,
                invoice_item_id=item.id,
                review_type="missing_manufacturer_code",
                priority="HIGH",
                status="open",
                prompt_text="Θα χρησιμοποιηθεί ο κωδικός προμηθευτή ως κωδικός κατασκευαστή;",
                payload_json={
                    "supplier_code": product.supplier_code,
                    "description": product.description,
                    "options": [
                        "Ναι, χρήση ως manufacturer code",
                        "Όχι, το προϊόν δεν έχει manufacturer code",
                        "Εισαγωγή χειροκίνητα",
                    ],
                },
            )
            db.add(review)

        # 2. Low confidence (< 90%) → HIGH priority
        if item.match_confidence and item.match_confidence < Decimal("90"):
            review = ReviewQueueItem(
                product_id=product.id,
                invoice_item_id=item.id,
                review_type="low_confidence",
                priority="HIGH",
                status="open",
                payload_json={"match_confidence": float(item.match_confidence)},
            )
            db.add(review)


async def _generate_ergalyon_code(db: AsyncSession) -> str:
    """Auto-generate επόμενο ERG-XXXXXXXX code. (§1.4 P2)"""
    result = await db.execute(
        select(Product.ergalyon_code)
        .where(Product.ergalyon_code.like('ERG-%'))
        .order_by(Product.ergalyon_code.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last and last.startswith('ERG-'):
        try:
            num = int(last[4:]) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"ERG-{num:08d}"


async def _process_file(invoice: Invoice, content: bytes, db: AsyncSession) -> dict:
    """Dispatch to appropriate parser based on invoice.file_format."""
    if invoice.file_format == "xml":
        return await _process_xml(invoice, content, db)
    elif invoice.file_format == "pdf":
        return await _process_pdf(invoice, content, db)
    elif invoice.file_format in ("excel", "xlsx", "xls", "csv"):
        return await _process_excel(invoice, content, db)
    elif invoice.file_format == "image":
        return await _process_image(invoice, content, db)
    else:
        raise ValueError(f"Unsupported file format: {invoice.file_format}")


async def _process_pdf(invoice: Invoice, content: bytes, db: AsyncSession) -> dict:
    """Parse PDF using PDFParser."""
    parser = PDFParser(content)
    parsed_list = parser.parse_all()
    if not parsed_list:
        raise ValueError("No invoices found in PDF")
    parsed = parsed_list[0]
    items_created = 0
    total_net = Decimal("0")
    for idx, line in enumerate(parsed["lines"], start=1):
        item = InvoiceItem(
            invoice_id=invoice.id,
            line_number=idx,
            raw_supplier_code=line["supplier_code"],
            raw_description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_total=line["line_total"],
        )
        db.add(item)
        items_created += 1
        total_net += line["line_total"]
    return {
        "confidence": parsed.get("confidence", 100.0),
        "total_net": total_net,
        "items_created": items_created,
    }


async def _process_excel(invoice: Invoice, content: bytes, db: AsyncSession) -> dict:
    """Parse Excel/CSV using ExcelParser."""
    filename = os.path.basename(invoice.file_path)
    parser = ExcelParser(content, filename)
    parsed_list = parser.parse_all()
    if not parsed_list:
        raise ValueError("No invoices found in Excel/CSV")
    parsed = parsed_list[0]
    items_created = 0
    total_net = Decimal("0")
    for idx, line in enumerate(parsed["lines"], start=1):
        item = InvoiceItem(
            invoice_id=invoice.id,
            line_number=idx,
            raw_supplier_code=line["supplier_code"],
            raw_description=line["description"],
            quantity=line["quantity"],
            unit_price=line["unit_price"],
            line_total=line["line_total"],
        )
        db.add(item)
        items_created += 1
        total_net += line["line_total"]
    return {
        "confidence": parsed.get("confidence", 100.0),
        "total_net": total_net,
        "items_created": items_created,
    }
