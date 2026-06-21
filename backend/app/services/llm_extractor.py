# EDM v2.1 — LLM Extractor Service
# Uses FreeLLMAPI to extract structured fields from raw text (OCR output).
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("edm.llm_extractor")

# Prompt for extracting product line items from raw OCR text
EXTRACTION_PROMPT = """
You are an expert at extracting product information from OCR text of invoices, catalogs, or price lists.
Given the following raw text, extract each product as a JSON object with the fields:
- supplier_code: The product code from the supplier (alphanumeric, may contain hyphens).
- description: The product description.
- qty: Quantity as a number (if present, else null).
- unit_price: Unit price as a number (if present, else null).
- line_total: Line total as a number (if present, else null).
- vat_rate: VAT rate as a number (if present, else null).
- description_normalized: Normalized description (lowercase, extra spaces removed).

Return a JSON list of objects. If no products are found, return an empty list.
If a field is not present or unclear, set it to null.

Raw text:
{raw_text}

JSON output:
"""


async def extract_from_text(raw_text: str) -> List[Dict[str, Any]]:
    """
    Use FreeLLMAPI to extract product line items from raw OCR text.
    Returns a list of dicts, each representing a product line.
    """
    if not settings.FREELLM_API_KEY or not settings.FREELLM_BASE_URL:
        logger.warning("FreeLLM API not configured; returning empty extraction.")
        return []

    url = f"{settings.FREELLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.FREELLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.FREELLM_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a data extraction expert."},
            {"role": "user", "content": EXTRACTION_PROMPT.format(raw_text=raw_text)},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "[]")
            # The response should be a JSON string representing a list.
            # Sometimes the model returns a JSON object with a key; we try to parse.
            try:
                extracted = json.loads(content)
                if isinstance(extracted, dict):
                    # If it's a dict, maybe it's wrapped in a key like "products"
                    # We'll try to find a list inside.
                    for v in extracted.values():
                        if isinstance(v, list):
                            extracted = v
                            break
                    else:
                        extracted = []
                elif not isinstance(extracted, list):
                    extracted = []
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"LLM extraction did not return valid JSON list: {content}")
                extracted = []
            return extracted
        except Exception as e:
            logger.error(f"FreeLLM API call failed: {e}")
            return []


