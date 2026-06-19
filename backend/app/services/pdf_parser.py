# EDM v2 — PDF Parser Service (§9.2)
# Structured PDF extraction using pdfplumber, with camelot fallback.

import logging
from decimal import Decimal
from typing import List, Optional

import pdfplumber

logger = logging.getLogger(__name__)

class PDFParser:
    """
    Parser for structured PDF invoices (text-based, not scanned).
    Uses pdfplumber to extract tables and rows.
    Falls back to camelot if needed.
    Confidence: 90-98% for well-formed tables.
    """

    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes

    def parse_all(self) -> List[dict]:
        """
        Parse the PDF and return a list of invoice dicts.
        Each dict mimics the structure expected by the processing pipeline:
        {
            'lines': [
                {
                    'supplier_code': str,
                    'description': str,
                    'quantity': Decimal,
                    'unit_price': Decimal,
                    'line_total': Decimal,
                },
                ...
            ],
            'total_net': Decimal,
            'total_vat': Optional[Decimal],
            'total_gross': Optional[Decimal],
            'confidence': float,
        }
        For simplicity, we treat the whole PDF as a single invoice.
        """
        try:
            return self._parse_with_pdfplumber()
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}; trying camelot")
            try:
                return self._parse_with_camelot()
            except Exception as e2:
                logger.error(f"Both parsers failed: {e2}")
                return []

    def _parse_with_pdfplumber(self) -> List[dict]:
        """Extract tables using pdfplumber."""
        lines = []
        with pdfplumber.open(self.pdf_bytes) as pdf:
            for page in pdf.pages:
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    # Assume first row is header
                    header = [str(cell).strip().lower() if cell else '' for cell in table[0]]
                    # Map columns to expected fields (simple heuristic)
                    # We'll look for known keywords
                    code_idx = self._find_idx(header, ['code', 'item code', 'supplier code', 'κωδικός'])
                    desc_idx = self._find_idx(header, ['description', 'item description', 'περιγραφή'])
                    qty_idx = self._find_idx(header, ['quantity', 'ποσότητα', 'qty'])
                    price_idx = self._find_idx(header, ['unit price', 'price', 'τιμή μονάδας', 'unit_price'])
                    total_idx = self._find_idx(header, ['line total', 'total', 'συνολικό'])
                    for row in table[1:]:
                        if len(row) <= max(filter(None, [code_idx, desc_idx, qty_idx, price_idx, total_idx])):
                            continue
                        code = str(row[code_idx]).strip() if code_idx is not None and code_idx < len(row) else ''
                        desc = str(row[desc_idx]).strip() if desc_idx is not None and desc_idx < len(row) else ''
                        qty_str = str(row[qty_idx]).strip() if qty_idx is not None and qty_idx < len(row) else '0'
                        price_str = str(row[price_idx]).strip() if price_idx is not None and price_idx < len(row) else '0'
                        total_str = str(row[total_idx]).strip() if total_idx is not None and total_idx < len(row) else '0'
                        try:
                            qty = Decimal(qty_str) if qty_str else Decimal('0')
                            unit_price = Decimal(price_str) if price_str else Decimal('0')
                            line_total = Decimal(total_str) if total_str else qty * unit_price
                        except Exception:
                            qty = Decimal('0')
                            unit_price = Decimal('0')
                            line_total = Decimal('0')
                        if code and desc:
                            lines.append({
                                'supplier_code': code,
                                'description': desc,
                                'quantity': qty,
                                'unit_price': unit_price,
                                'line_total': line_total,
                            })
        # Calculate totals
        total_net = sum(l['line_total'] for l in lines)
        # For simplicity, we don't extract VAT from PDF here; could be added.
        confidence = 0.95 if lines else 0.0
        return [{
            'lines': lines,
            'total_net': total_net,
            'total_vat': None,
            'total_gross': total_net,  # assuming no VAT
            'confidence': confidence,
        }]

    def _parse_with_camelot(self) -> List[dict]:
        """Fallback to camelot."""
        import camelot
        # Write bytes to temp file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(self.pdf_bytes)
            tmp_path = tmp.name
        try:
            tables = camelot.read_pdf(tmp_path, pages='all')
            lines = []
            for table in tables:
                df = table.df
                if df.shape[0] < 2:
                    continue
                # Assume first row is header
                header = [str(c).strip().lower() for c in df.iloc[0].tolist()]
                code_idx = self._find_idx(header, ['code', 'item code', 'supplier code', 'κωδικός'])
                desc_idx = self._find_idx(header, ['description', 'item description', 'περιγραφή'])
                qty_idx = self._find_idx(header, ['quantity', 'ποσότητα', 'qty'])
                price_idx = self._find_idx(header, ['unit price', 'price', 'τιμή μονάδας', 'unit_price'])
                total_idx = self._find_idx(header, ['line total', 'total', 'συνολικό'])
                for _, row in df.iloc[1:].iterrows():
                    if len(row) <= max(filter(None, [code_idx, desc_idx, qty_idx, price_idx, total_idx])):
                        continue
                    code = str(row[code_idx]).strip() if code_idx is not None and code_idx < len(row) else ''
                    desc = str(row[desc_idx]).strip() if desc_idx is not None and desc_idx < len(row) else ''
                    qty_str = str(row[qty_idx]).strip() if qty_idx is not None and qty_idx < len(row) else '0'
                    price_str = str(row[price_idx]).strip() if price_idx is not None and price_idx < len(row) else '0'
                    total_str = str(row[total_idx]).strip() if total_idx is not None and total_idx < len(row) else '0'
                    try:
                        qty = Decimal(qty_str) if qty_str else Decimal('0')
                        unit_price = Decimal(price_str) if price_str else Decimal('0')
                        line_total = Decimal(total_str) if total_str else qty * unit_price
                    except Exception:
                        qty = Decimal('0')
                        unit_price = Decimal('0')
                        line_total = Decimal('0')
                    if code and desc:
                        lines.append({
                            'supplier_code': code,
                            'description': desc,
                            'quantity': qty,
                            'unit_price': unit_price,
                            'line_total': line_total,
                        })
            total_net = sum(l['line_total'] for l in lines)
            confidence = 0.90 if lines else 0.0
            return [{
                'lines': lines,
                'total_net': total_net,
                'total_vat': None,
                'total_gross': total_net,
                'confidence': confidence,
            }]
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _find_idx(self, header: List[str], keywords: List[str]) -> Optional[int]:
        for i, h in enumerate(header):
            if any(k in h for k in keywords):
                return i
        return None
