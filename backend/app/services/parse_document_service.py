"""
EDM v2.1 — Parse Document service.
Orchestrates parsers based on file type and supplier parsing profile.
"""
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
        import tempfile
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
                    "extraction_source": "xml",
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
        # Basic OCR using pytesseract if available
        from PIL import Image
        import io
        try:
            import pytesseract
            img = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(img, lang="ell+eng")
            if text.strip():
                return ParseResult(
                    doc_kind="unknown",
                    confidence=0.60,
                    parser_version="image-ocr-v1.0",
                    header_json={"extracted_text_preview": text[:500]},
                )
        except ImportError:
            pass
        return ParseResult(
            doc_kind="unknown",
            confidence=0.50,
            parser_version="image-v1.0",
            header_json={"note": "Image uploaded; full OCR depends on tesseract availability"},
        )
    except Exception as e:
        return ParseResult(error_message=f"Image parsing failed: {e}")


def parse_document_sync(content: bytes, file_type: str, supplier_parser: Optional[str] = None) -> ParseResult:
    """
    Parse a document based on file_type and optional supplier parser override.
    Runs synchronously (called from Celery task).
    """
    parser_override = supplier_parser or file_type

    if parser_override == "xml":
        return _parse_xml(content)
    elif parser_override == "pdf":
        return _parse_pdf(content)
    elif parser_override in ("xlsx", "excel"):
        return _parse_excel(content)
    elif parser_override in ("img", "image"):
        return _parse_image(content, file_type)
    else:
        # Auto-detect by file_type
        if file_type == "xml":
            return _parse_xml(content)
        elif file_type == "pdf":
            return _parse_pdf(content)
        elif file_type in ("xlsx", "xls"):
            return _parse_excel(content)
        elif file_type == "img":
            return _parse_image(content, file_type)
        else:
            return ParseResult(error_message=f"Unknown file type: {file_type}")