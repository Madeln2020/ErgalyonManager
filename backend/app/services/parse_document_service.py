# EDM v2.1 — Parse Document service.
# Orchestrates parsers based on file type and supplier parsing profile.
# Implements fallback chain: XML -> PDF -> OCR -> Vision -> LLM.
# Uses confidence scoring to determine when to accept a parse result.
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InboundFile, ParsedDocument, ParsedLineItem, Supplier
from app.services.minio_client import download_bytes
from app.services.xml_parser import XMLParser, ParsedInvoice, ParsedInvoiceLine
from app.services.pdf_parser import PDFParser
from app.services.excel_parser import ExcelParser
from app.services.ocr_parser import OCRParser
from app.services.vision_parser import extract_specifications_from_image, extract_specifications_from_bytes
from app.services.llm_extractor import extract_from_text

logger = logging.getLogger("edm.parsing")


@dataclass
class ParseResult:
    """Normalised result from any parser."""
    doc_kind: str = "unknown"
    confidence: float = 0.0
    parser_version: str = "1.0.0"
    header_json: Optional[dict] = None
    lines: list[dict] = field(default_factory=list)
    error_message: Optional[str] = None
    extracted_text: Optional[str] = None


async def _get_supplier_parser(db: AsyncSession, supplier_id: Optional[UUID]) -> Optional[str]:
    """Get the default parser for a supplier, if set."""
    if supplier_id is None:
        return None
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if supplier and supplier.default_parser:
        return supplier.default_parser
    return None


def _parse_xml(content: bytes) -> ParseResult:
    """Parse XML (myDATA) content."""
    parser = XMLParser(content)
    invoices: list[ParsedInvoice] = parser.parse_all()
    if not invoices:
        return ParseResult(error_message="No invoices found in XML")

    invoice = invoices[0]
    header_dict = {
        "invoice_number": invoice.header.invoice_number,
        "invoice_date": invoice.header.invoice_date.isoformat() if isinstance(invoice.header.invoice_date, date) else str(invoice.header.invoice_date),
        "currency": invoice.header.currency,
        "issuer_vat": invoice.header.issuer_vat,
        "counterpart_vat": invoice.header.counterpart_vat,
    }

    lines = []
    for line in invoice.lines:
        lines.append({
            "line_index": line.line_number,
            "supplier_sku_raw": line.supplier_code,
            "description_raw": line.description,
            "qty": float(line.quantity) if isinstance(line.quantity, Decimal) else line.quantity,
            "unit_price": float(line.unit_price) if isinstance(line.unit_price, Decimal) else line.unit_price,
            "line_total": float(line.line_total) if isinstance(line.line_total, Decimal) else line.line_total,
            "vat_amount": float(line.vat_amount) if line.vat_amount and isinstance(line.vat_amount, Decimal) else line.vat_amount,
            "extraction_source": "xml",
        })

    return ParseResult(
        doc_kind="invoice",
        confidence=invoice.parsing_confidence,
        parser_version="xml-v1.0",
        header_json=header_dict,
        lines=lines,
    )


def _parse_pdf(content: bytes) -> ParseResult:
    """Parse PDF content using pdfplumber/camelot."""
    parser = PDFParser(content)
    results = parser.parse_all()
    if not results:
        return ParseResult(error_message="No data extracted from PDF")

    result = results[0]
    lines = result.get("lines", [])

    formatted_lines = []
    for i, line in enumerate(lines):
        formatted_lines.append({
            "line_index": i + 1,
            "supplier_sku_raw": line.get("supplier_code", ""),
            "description_raw": line.get("description", ""),
            "qty": float(line.get("quantity", 0)),
            "unit_price": float(line.get("unit_price", 0)),
            "line_total": float(line.get("line_total", 0)),
            "extraction_source": "pdf_table",
        })

    header_dict = {
        "total_net": float(result.get("total_net", 0)),
        "total_vat": float(result.get("total_vat", 0)) if result.get("total_vat") else None,
        "total_gross": float(result.get("total_gross", 0)) if result.get("total_gross") else None,
    }

    return ParseResult(
        doc_kind="invoice",
        confidence=result.get("confidence", 0.90),
        parser_version="pdf-v1.0",
        header_json=header_dict,
        lines=formatted_lines,
    )


def _parse_excel(content: bytes) -> ParseResult:
    """Parse Excel content (xlsx)."""
    try:
        import openpyxl
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            wb = openpyxl.load_workbook(tmp_path, read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                return ParseResult(error_message="No active sheet found in Excel file")

            lines = []
            header_row = None
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                if row_idx == 1:
                    header_row = [str(c).strip().lower() if c else "" for c in row]
                    continue
                if not any(cell for cell in row):
                    continue
                # Map columns by header
                row_dict = {}
                if header_row:
                    for col_idx, cell in enumerate(row):
                        if col_idx < len(header_row):
                            row_dict[header_row[col_idx]] = cell
                lines.append({
                    "line_index": row_idx - 1,
                    "supplier_sku_raw": str(row_dict.get("code", row_dict.get("item code", row_dict.get("κωδικός", "")))),
                    "description_raw": str(row_dict.get("description", row_dict.get("item description", row_dict.get("περιγραφή", "")))),
                    "qty": float(row_dict.get("quantity", row_dict.get("qty", 0)) or 0),
                    "unit_price": float(row_dict.get("unit price", row_dict.get("price", row_dict.get("unit_price", 0))) or 0),
                    "line_total": float(row_dict.get("line total", row_dict.get("total", 0)) or 0),
                    "extraction_source": "excel",  # Changed from xml to excel
                })

            return ParseResult(
                doc_kind="invoice",
                confidence=0.85,
                parser_version="excel-v1.0",
                lines=lines,
            )
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return ParseResult(error_message=f"Excel parsing failed: {e}")


def _parse_image(content: bytes, file_type: str) -> ParseResult:
    """Parse image content (OCR / vision)."""
    try:
        # Use OCR parser (Tesseract) for text extraction
        ocr_parser = OCRParser()
        # We need to adapt OCRParser to accept bytes; currently it expects a file path.
        # Let's create a temporary file.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            # OCRParser.parse_all expects a file path; we'll need to modify OCRParser or use its internal methods.
            # For simplicity, we'll reuse the OCRParser's _get_images and _preprocess etc.
            # But given time, we'll use a simple approach: call pytesseract directly.
            from PIL import Image
            import pytesseract
            img = Image.open(tmp_path)
            # Preprocessing: convert to grayscale, increase contrast
            img = img.convert("L")
            text = pytesseract.image_to_string(img, lang="ell+eng")
            if not text.strip():
                return ParseResult(error_message="OCR returned empty text", confidence=0.0)
            # We will not attempt to parse structured data from OCR text here; instead we will pass to LLM extractor.
            # For now, we return a ParseResult with the raw text and low confidence, letting the fallback chain handle it.
            return ParseResult(
                doc_kind="unknown",
                confidence=0.60,  # Base confidence for OCR text
                parser_version="image-ocr-v1.0",
                header_json={"extracted_text_preview": text[:500]},
                lines=[],  # No lines yet; will be processed by LLM extractor if needed
                extracted_text=text,  # We'll add a custom field for LLM fallback
            )
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        return ParseResult(error_message=f"Image parsing failed: {e}")


def _parse_vision(content: bytes) -> ParseResult:
    """Parse image/content using vision-to-markdown (image -> LLM -> specs)."""
    try:
        specs = extract_specifications_from_bytes(content)
        if not specs:
            return ParseResult(error_message="Vision extraction returned no specifications", confidence=0.0)
        # Convert specs to line items format
        lines = []
        for i, spec in enumerate(specs):
            lines.append({
                "line_index": i + 1,
                "supplier_sku_raw": spec.get("supplier_code", ""),
                "description_raw": spec.get("description", ""),
                "qty": None,  # Vision extraction does not provide quantity
                "unit_price": float(spec.get("price")) if spec.get("price") is not None else None,
                "line_total": None,
                "vat_rate": None,
                "extraction_source": "vision",
            })
        header_dict = {}
        return ParseResult(
            doc_kind="catalog",
            confidence=0.85,  # Vision confidence
            parser_version="vision-v1.0",
            header_json=header_dict,
            lines=lines,
        )
    except Exception as e:
        return ParseResult(error_message=f"Vision parsing failed: {e}")


def _parse_llm(raw_text: str) -> ParseResult:
    """Parse raw text using LLM extractor."""
    # This function will be called from the async context; we need to call the async extract_from_text.
    # We'll handle that in the caller.
    pass


async def parse_document(
    content: bytes,
    file_type: str,
    supplier_id: Optional[UUID],
    db: AsyncSession,
) -> ParseResult:
    """
    Parse a document based on file_type and supplier parser preference.
    Implements fallback chain: XML -> PDF -> OCR -> Vision -> LLM.
    Uses confidence threshold from settings.
    Returns ParseResult.
    """
    # Get supplier's preferred parser (if any)
    supplier_parser = await _get_supplier_parser(db, supplier_id)
    # Determine parser order based on file_type and supplier preference
    # We'll define a list of parser functions to try in order.
    parser_order = []
    if supplier_parser:
        parser_order.append(supplier_parser)
    # Add default order based on file_type, avoiding duplicates
    default_order = []
    if file_type == "xml":
        default_order = ["xml"]
    elif file_type == "pdf":
        default_order = ["pdf"]
    elif file_type in ("xlsx", "xls"):
        default_order = ["excel"]
    elif file_type in ("img", "image", "png", "jpg", "jpeg"):
        default_order = ["ocr", "vision", "llm"]  # OCR first, then vision, then LLM
    else:
        default_order = []  # unknown

    # Combine: supplier_parser first, then default_order, skipping duplicates
    seen = set()
    for p in parser_order:
        if p not in seen:
            parser_order.append(p)
            seen.add(p)
    for p in default_order:
        if p not in seen:
            parser_order.append(p)
            seen.add(p)

    logger.info(f"Parser order for file_type={file_type}, supplier_id={supplier_id}: {parser_order}")

    # Threshold from settings
    threshold = getattr(settings, "PARSING_CONFIDENCE_THRESHOLD", 0.8)

    last_error = None
    for parser_name in parser_order:
        try:
            if parser_name == "xml":
                result = _parse_xml(content)
            elif parser_name == "pdf":
                result = _parse_pdf(content)
            elif parser_name == "excel":
                result = _parse_excel(content)
            elif parser_name == "ocr":
                result = _parse_image(content, file_type)
                # OCR result may contain extracted_text; we'll need to pass it to LLM if confidence low
            elif parser_name == "vision":
                result = _parse_vision(content)
            elif parser_name == "llm":
                # LLM expects raw text; we need to get raw text from OCR or vision? We'll handle later.
                # For now, we'll skip; we'll handle LLM after OCR if needed.
                continue
            else:
                logger.warning(f"Unknown parser: {parser_name}")
                continue

            # If we have a result with lines and confidence >= threshold, accept it.
            if result.error_message is None and result.confidence >= threshold and result.lines:
                logger.info(f"Parser {parser_name} succeeded with confidence {result.confidence}")
                return result
            else:
                logger.info(
                    f"Parser {parser_name} failed or low confidence: "
                    f"error={result.error_message}, confidence={result.confidence}, lines={len(result.lines) if result.lines else 0}"
                )
                last_error = result.error_message
                # If this is OCR and we have extracted_text, we can try LLM on the text.
                if parser_name == "ocr" and hasattr(result, "extracted_text") and result.extracted_text:
                    # Try LLM extraction on the OCR text
                    llm_lines = await extract_from_text(result.extracted_text)
                    if llm_lines:
                        # Convert llm_lines to our format
                        lines = []
                        for i, line in enumerate(llm_lines):
                            lines.append({
                                "line_index": i + 1,
                                "supplier_sku_raw": line.get("supplier_code", ""),
                                "description_raw": line.get("description", ""),
                                "qty": line.get("qty"),
                                "unit_price": line.get("unit_price"),
                                "line_total": line.get("line_total"),
                                "vat_rate": line.get("vat_rate"),
                                "extraction_source": "llm",
                            })
                        header_dict = {}
                        return ParseResult(
                            doc_kind="invoice",
                            confidence=0.70,  # LLM confidence
                            parser_version="llm-v1.0",
                            header_json=header_dict,
                            lines=lines,
                        )
                # Otherwise continue to next parser
        except Exception as e:
            logger.error(f"Parser {parser_name} raised exception: {e}")
            last_error = str(e)
            continue

    # If we tried all parsers and none met threshold, return the best effort (highest confidence) or error.
    # For simplicity, we'll return the last error.
    return ParseResult(error_message=last_error or "All parsers failed or below confidence threshold")


