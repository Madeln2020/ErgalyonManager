# EDM v2 — Excel Parser Service (§9.5)
# Parses .xlsx/.csv files using pandas/openpyxl.

import logging
from decimal import Decimal
from io import BytesIO
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

class ExcelParser:
    """
    Parser for Excel/CSV invoice lists.
    Uses pandas to read sheets, assumes header row with column names.
    Confidence: 95-100% for structured data.
    """

    def __init__(self, file_bytes: bytes, filename: str):
        self.file_bytes = file_bytes
        self.filename = filename.lower()

    def parse_all(self) -> List[dict]:
        """
        Parse the Excel/CSV and return a list of invoice dicts.
        Each dict matches the format expected by the processing pipeline.
        For simplicity, treat the whole file as a single invoice.
        """
        try:
            if self.filename.endswith('.csv'):
                df = pd.read_csv(BytesIO(self.file_bytes))
            elif self.filename.endswith('.xls'):
                df = pd.read_excel(BytesIO(self.file_bytes), engine='xlrd')
            else:
                # Assume .xlsx
                df = pd.read_excel(BytesIO(self.file_bytes), engine='openpyxl')
        except Exception as e:
            logger.error(f"Failed to read Excel/CSV: {e}")
            return []

        if df.empty:
            return []

        # Normalize column names
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Map columns to expected fields (heuristic)
        code_idx = self._find_idx(df.columns, ['code', 'item code', 'supplier code', 'κωδικός'])
        desc_idx = self._find_idx(df.columns, ['description', 'item description', 'περιγραφή'])
        qty_idx = self._find_idx(df.columns, ['quantity', 'ποσότητα', 'qty'])
        price_idx = self._find_idx(df.columns, ['unit price', 'price', 'τιμή μονάδας', 'unit_price'])
        total_idx = self._find_idx(df.columns, ['line total', 'total', 'συνολικό'])

        lines = []
        for _, row in df.iterrows():
            # Skip rows where all essential fields are empty
            code = str(row.iloc[code_idx]).strip() if code_idx is not None and code_idx < len(row) else ''
            desc = str(row.iloc[desc_idx]).strip() if desc_idx is not None and desc_idx < len(row) else ''
            qty_str = str(row.iloc[qty_idx]).strip() if qty_idx is not None and qty_idx < len(row) else '0'
            price_str = str(row.iloc[price_idx]).strip() if price_idx is not None and price_idx < len(row) else '0'
            total_str = str(row.iloc[total_idx]).strip() if total_idx is not None and total_idx < len(row) else '0'
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
        confidence = 0.98 if lines else 0.0
        return [{
            'lines': lines,
            'total_net': total_net,
            'total_vat': None,
            'total_gross': total_net,  # assuming no VAT
            'confidence': confidence,
        }]

    def _find_idx(self, columns: List[str], keywords: List[str]) -> Optional[int]:
        for i, col in enumerate(columns):
            if any(k in col for k in keywords):
                return i
        return None
