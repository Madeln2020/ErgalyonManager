import io
import pytesseract
from PIL import Image
from typing import Dict, Any

def parse_image(file_path: str) -> Dict[str, Any]:
    """Parse a scanned invoice image and extract minimal fields.
    Returns a dict with keys: invoice_number, invoice_date, total_amount, currency, confidence.
    The implementation is naive – it runs OCR on the whole image and then uses simple regexes.
    """
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    # Simple regex extraction (Greek/English numbers)
    import re
    invoice_number = None
    invoice_date = None
    total_amount = None
    currency = None
    # Look for pattern like "Invoice № 12345" or "Invoice #: 12345"
    m = re.search(r"Invoice\s*(?:#|№|No\.?|Number)\s*[:]?\s*(\S+)", text, re.IGNORECASE)
    if m:
        invoice_number = m.group(1)
    # Date pattern dd/mm/yyyy or yyyy-mm-dd
    m = re.search(r"(\d{2}[./-]\d{2}[./-]\d{4}|\d{4}[./-]\d{2}[./-]\d{2})", text)
    if m:
        invoice_date = m.group(1)
    # Total amount pattern
    m = re.search(r"Total[:]?\s*([\d,.]+)\s*([A-Z]{3})", text, re.IGNORECASE)
    if m:
        total_amount = float(m.group(1).replace(',', '.'))
        currency = m.group(2)
    # Confidence approximation: number of recognized words / total words
    words = re.findall(r"\w+", text)
    confidence = min(1.0, len(words) / 200.0)  # heuristic
    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "total_amount": total_amount,
        "currency": currency,
        "confidence": confidence,
        "raw_text": text,
    }
