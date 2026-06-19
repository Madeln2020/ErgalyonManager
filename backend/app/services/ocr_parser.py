# EDM v2 — OCR Parser Service (§9.4)
# Handles scanned invoices, images (JPG/PNG) and catalog PDFs.
# Primary: Tesseract (local), Fallback: Google Vision API

import io
import logging
import tempfile
from decimal import Decimal
from typing import List, Optional

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRParser:
    """
    OCR parser for scanned invoices and images.
    Confidence: 60-90% depending on image quality.
    Low-confidence results (<80%) are routed to Review Queue.
    """

    # Languages: Greek + English
    TESSERACT_LANG = "ell+eng"

    def __init__(self, image_bytes: bytes, filename: str = ""):
        self.image_bytes = image_bytes
        self.filename = filename.lower()

    def parse_all(self) -> List[dict]:
        """
        Parse the image/PDF and return a list of invoice dicts.
        Returns structure matching the processing pipeline format.
        """
        try:
            # Try Tesseract first (local, no API key needed)
            return self._parse_with_tesseract()
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}; trying Google Vision")
            try:
                return self._parse_with_google_vision()
            except Exception as e2:
                logger.error(f"Both OCR parsers failed: {e2}")
                return []

    def _parse_with_tesseract(self) -> List[dict]:
        """Extract text from image using Tesseract, then parse structured data."""
        # Convert PDF pages to images first if needed
        images = self._get_images()

        all_text = ""
        for img in images:
            # Pre-processing: convert to grayscale, increase contrast
            processed = self._preprocess(img)
            text = pytesseract.image_to_string(
                processed,
                lang=self.TESSERACT_LANG,
                config="--psm 6",  # Assume uniform block of text
            )
            all_text += text + "\n"

        if not all_text.strip():
            return []

        # Parse extracted text into structured invoice data
        lines = self._parse_ocr_text(all_text)

        total_net = sum(l["line_total"] for l in lines)
        # OCR is inherently less confident than structured parsers
        confidence = 0.85 if len(lines) > 0 else 0.0
        # Reduce confidence for low-quality text (many garbled characters)
        if self._has_garbled_text(all_text):
            confidence = 0.60

        return [{
            "lines": lines,
            "total_net": total_net,
            "total_vat": None,
            "total_gross": total_net,
            "confidence": confidence,
            "ocr_raw_text": all_text.strip(),
        }]

    def _parse_with_google_vision(self) -> List[dict]:
        """Fallback: use Google Cloud Vision API for OCR."""
        try:
            from google.cloud import vision

            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=self.image_bytes)

            response = client.text_detection(image=image)
            if response.error.message:
                raise RuntimeError(f"Google Vision API error: {response.error.message}")

            texts = response.text_annotations
            if not texts:
                return []

            all_text = texts[0].description

            lines = self._parse_ocr_text(all_text)
            total_net = sum(l["line_total"] for l in lines)
            confidence = 0.90 if len(lines) > 0 else 0.0

            return [{
                "lines": lines,
                "total_net": total_net,
                "total_vat": None,
                "total_gross": total_net,
                "confidence": confidence,
                "ocr_raw_text": all_text.strip(),
            }]
        except ImportError:
            logger.error("google-cloud-vision not installed")
            return []
        except Exception as e:
            logger.error(f"Google Vision failed: {e}")
            return []

    def _get_images(self) -> List[Image.Image]:
        """Convert input bytes to PIL Images. Handles PDF and image files."""
        if self.filename.endswith(".pdf"):
            return self._pdf_to_images()
        else:
            # Direct image (JPG, PNG, etc.)
            img = Image.open(io.BytesIO(self.image_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
            return [img]

    def _pdf_to_images(self) -> List[Image.Image]:
        """Convert PDF pages to images using pdfplumber."""
        import pdfplumber

        images = []
        with pdfplumber.open(io.BytesIO(self.image_bytes)) as pdf:
            for page in pdf.pages:
                # Render page to image
                img = page.to_image(resolution=300)
                pil_img = img.original.convert("RGB")
                images.append(pil_img)
        return images

    def _preprocess(self, img: Image.Image) -> Image.Image:
        """Pre-process image for better OCR results."""
        # Convert to grayscale
        if img.mode != "L":
            gray = img.convert("L")
        else:
            gray = img

        # Resize if too small (min 300 DPI equivalent)
        width, height = gray.size
        if width < 1000:
            scale = 1000 / width
            gray = gray.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

        # Increase contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(gray)
        gray = enhancer.enhance(1.5)

        # Sharpen
        enhancer = ImageEnhance.Sharpness(gray)
        gray = enhancer.enhance(1.3)

        return gray

    def _parse_ocr_text(self, text: str) -> List[dict]:
        """
        Parse OCR-extracted text into structured invoice lines.
        Uses heuristic pattern matching for product line extraction.
        
        Looks for patterns like:
        - CODE  DESCRIPTION  QTY  PRICE  TOTAL
        - Lines with numeric codes followed by text and prices
        """
        lines = []
        text_lines = text.strip().split("\n")
        
        for line_text in text_lines:
            line_text = line_text.strip()
            if not line_text or len(line_text) < 5:
                continue

            parsed = self._try_parse_line(line_text)
            if parsed:
                lines.append(parsed)

        return lines

    def _try_parse_line(self, line_text: str) -> Optional[dict]:
        """
        Try to parse a single text line into a product line.
        Heuristic: look for patterns with code + description + price(s).
        """
        import re

        # Pattern 1: CODE  DESCRIPTION  QTY  UNIT_PRICE  LINE_TOTAL
        # Matches lines like: "03-12345  ΣΕΓΑ ΣΠΑΘΟΥ BOSCH  2  42.75  85.50"
        pattern1 = re.compile(
            r"^([A-Za-z0-9\-]+)\s+"      # Code
            r"(.+?)\s+"                     # Description (non-greedy)
            r"(\d+[\.,]?\d*)\s+"           # Quantity
            r"(\d+[\.,]\d{2})\s+"          # Unit Price
            r"(\d+[\.,]\d{2})\s*$"         # Line Total
        )
        m = pattern1.match(line_text)
        if m:
            code, desc, qty, price, total = m.groups()
            return {
                "supplier_code": code.strip(),
                "description": desc.strip(),
                "quantity": self._safe_decimal(qty),
                "unit_price": self._safe_decimal(price),
                "line_total": self._safe_decimal(total),
            }

        # Pattern 2: CODE  DESCRIPTION  PRICE (simpler, no qty)
        pattern2 = re.compile(
            r"^([A-Za-z0-9\-]+)\s+"      # Code
            r"(.+?)\s+"                     # Description
            r"(\d+[\.,]\d{2})\s*$"         # Price at end
        )
        m = pattern2.match(line_text)
        if m:
            code, desc, price = m.groups()
            return {
                "supplier_code": code.strip(),
                "description": desc.strip(),
                "quantity": self._safe_decimal("1"),
                "unit_price": self._safe_decimal(price),
                "line_total": self._safe_decimal(price),
            }

        # Pattern 3: Just CODE and DESCRIPTION (no prices detected)
        pattern3 = re.compile(
            r"^([A-Za-z0-9\-]{3,20})\s+"  # Code (3-20 chars)
            r"(.{10,})\s*$"                  # Description (at least 10 chars)
        )
        m = pattern3.match(line_text)
        if m:
            code, desc = m.groups()
            return {
                "supplier_code": code.strip(),
                "description": desc.strip(),
                "quantity": self._safe_decimal("1"),
                "unit_price": self._safe_decimal("0"),
                "line_total": self._safe_decimal("0"),
            }

        return None

    def _has_garbled_text(self, text: str) -> bool:
        """Detect if OCR output has many garbled/unrecognized characters."""
        if not text:
            return True
        # Count non-ASCII, non-Greek characters that might indicate OCR errors
        total_chars = len(text)
        if total_chars == 0:
            return True
        # Very rough heuristic: if more than 30% "strange" characters
        strange = sum(1 for c in text if not c.isalnum() and c not in ' \n\t.,;:()-/€$€£+=%"\'')
        return (strange / total_chars) > 0.3

    @staticmethod
    def _safe_decimal(val: str) -> Decimal:
        """Safely convert string to Decimal."""
        try:
            cleaned = val.replace(",", ".")
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")

# Helper function to match the old import style
def parse_image(file_path: str) -> dict:
    """Read an image/PDF file and return OCR‑parsed dict.
    This wrapper maintains backward compatibility with code that expected
    a ``parse_image(file_path)`` function.
    """
    with open(file_path, "rb") as f:
        data = f.read()
    # Use the filename for format detection inside OCRParser
    parser = OCRParser(data, filename=file_path)
    # OCRParser returns a list of invoice dicts; we take the first
    results = parser.parse_all()
    return results[0] if results else {}
