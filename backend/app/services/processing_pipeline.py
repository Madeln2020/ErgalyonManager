# EDM v2 – Processing Pipeline Service
# Handles different file types (xml, pdf, excel, image, catalog) and normalizes data

from typing import Any, Dict

from .xml_parser import XMLParser
from .pdf_parser import PDFParser
from .excel_parser import ExcelParser
from .ocr_parser import parse_image
from .vision_parser import parse_catalog


def _enqueue_enrichment(product_id: str, raw_text: str):
    """Lazily import and call the Celery enrichment task."""
    try:
        import sys
        import os
        # Add backend/ dir to path if not already there (celery_worker lives there)
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from celery_worker import enrich_product_task
        enrich_product_task.delay(product_id, raw_text)
    except Exception as exc:
        print(f"[ProcessingPipeline] Celery task enqueue failed: {exc}")

class ProcessingPipeline:
    """Dispatches files to the appropriate parser based on `file_format`.
    Returns a dict with parser‑specific keys (e.g. `invoice_number`, `catalog_specs`).
    """

    def __init__(self, db_session: Any = None):
        self.db = db_session  # placeholder – not used in this stub

    def _process_file(self, file_path: str, file_format: str) -> Dict[str, Any]:
        if file_format == "xml":
            return self._process_xml(file_path)
        elif file_format == "pdf":
            return self._process_pdf(file_path)
        elif file_format == "excel":
            return self._process_excel(file_path)
        elif file_format == "image":
            return self._process_image(file_path)
        elif file_format == "catalog":
            return self._process_catalog(file_path)
        else:
            raise ValueError(f"Unsupported file_format: {file_format}")

    def _process_xml(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            parser = XMLParser(f.read())
            invoices = parser.parse_all()
            return invoices[0].__dict__ if invoices else {}

    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
            parser = PDFParser(pdf_bytes)
            # For simplicity return the first parsed dict
            results = parser.parse_all()
            return results[0] if results else {}

    def _process_excel(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            filename = file_path.split('/')[-1]
            parser = ExcelParser(file_bytes, filename)
            results = parser.parse_all()
            return results[0] if results else {}

    def _process_image(self, file_path: str) -> Dict[str, Any]:
        result = parse_image(file_path)
        confidence = result.get("confidence", 0)
        # If confidence is high enough we return the parsed data directly.
        if confidence >= 0.85:
            return {
                "invoice_number": result.get("invoice_number"),
                "invoice_date": result.get("invoice_date"),
                "total_amount": result.get("total_amount"),
                "currency": result.get("currency"),
                "confidence": confidence,
                "raw_text": result.get("raw_text"),
                "queued": False,
            }
        # Low confidence – enqueue an asynchronous enrichment task via Celery.
        # In a real flow we would have a product_id linked to the OCR invoice.
        # Here we use a placeholder ID ("temp-id") to illustrate the pattern.
        _enqueue_enrichment("temp-id", result.get("raw_text", ""))
        return {
            "invoice_number": result.get("invoice_number"),
            "invoice_date": result.get("invoice_date"),
            "total_amount": result.get("total_amount"),
            "currency": result.get("currency"),
            "confidence": confidence,
            "raw_text": result.get("raw_text"),
            "queued": True,
        }


    def _process_catalog(self, file_path: str) -> Dict[str, Any]:
        specs = parse_catalog(file_path)
        return {"catalog_specs": specs, "confidence": 0.95}
