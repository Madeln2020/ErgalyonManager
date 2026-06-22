# EDM v2.1 — Vision Parser Service (supports FreeLLMAPI or Gemini)
# Extracts product specifications from images/catalog PDFs using a vision-capable LLM.
import json
import logging
import os
import tempfile
from typing import Any, Dict, List

import httpx

from app.config import settings

logger = logging.getLogger("edm.vision_parser")

# Determine which vision provider to use
_USE_FREELLM_VISION = bool(settings.FREELLM_VISION_MODEL and settings.FREELLM_API_KEY and settings.FREELLM_BASE_URL)
_USE_GEMINI = False
if not _USE_FREELLM_VISION:
    try:
        import google.generativeai as genai
        if os.environ.get("GEMINI_API_KEY"):
            genai.configure(api_key=os.environ["GEMINI_API_KEY"])
            _USE_GEMINI = True
        else:
            logger.warning("GEMINI_API_KEY not set; vision parser will return empty results.")
    except ImportError:
        logger.warning("google-generativeai not installed; vision parser will return empty results.")


def _extract_with_freellm_vision(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Use FreeLLMAPI (vision-capable model) to extract specifications from image.
    Returns list of dicts with keys: name, supplier_code, description, price, currency, image_url.
    """
    url = f"{settings.FREELLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.FREELLM_API_KEY}",
        "Content-Type": "application/json",
    }
    # Encode image as base64
    import base64
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    # Assuming the model accepts image in the content as per OpenAI vision format
    payload = {
        "model": settings.FREELLM_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Examine this catalog or invoice image carefully. Identify products and extract the following information for each one:\\n"
                            "- **name**: The product name.\\n"
                            "- **supplier_code**: The product code from the supplier. Look for numeric or alphanumeric codes near the name.\\n"
                            "- **description**: A brief description of the product.\\n"
                            "- **price**: The unit price of the product. Should be a number.\\n"
                            "- **currency**: The currency (e.g., EUR, USD). Prefer EUR.\\n"
                            "- **image_url**: If there is an explicit image URL for the product, otherwise leave blank.\\n\\n"
                            "Return the results as a JSON list of objects, where each object represents a product. "
                            "If no products are found, return an empty list. If you see paragraphs of text, try to separate them into products. "
                            "Ignore invoice summary information (e.g., total amount, VAT)."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
    }
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "[]")
        # Extract JSON from markdown if present
        if content.strip().startswith("```json"):
            content = content.strip()[7:-3].strip()
        extracted = json.loads(content)
        if not isinstance(extracted, list):
            logger.warning(f"FreeLLM vision did not return a list: {extracted}")
            return []
        # Ensure each item has the expected fields
        result = []
        for item in extracted:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "name": item.get("name"),
                    "supplier_code": item.get("supplier_code"),
                    "description": item.get("description"),
                    "price": item.get("price"),
                    "currency": item.get("currency", "EUR"),
                    "image_url": item.get("image_url"),
                    "source_file": "",  # will be filled by caller
                }
            )
        return result
    except Exception as e:
        logger.error(f"FreeLLM vision API call failed: {e}")
        return []


def _extract_with_gemini(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Use Gemini Vision model to extract specifications from image.
    Returns list of dicts with keys: name, supplier_code, description, price, currency, image_url.
    """
    try:
        import google.generativeai as genai
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel("gemini-pro-vision")
        prompt = (
            "Examine this catalog or invoice image carefully. Identify products and extract the following information for each one:\\n"
            "- **name**: The product name.\\n"
            "- **supplier_code**: The product code from the supplier. Look for numeric or alphanumeric codes near the name.\\n"
            "- **description**: A brief description of the product.\\n"
            "- **price**: The unit price of the product. Should be a number.\\n"
            "- **currency**: The currency (e.g., EUR, USD). Prefer EUR.\\n"
            "- **image_url**: If there is an explicit image URL for the product, otherwise leave blank.\\n\\n"
            "Return the results as a JSON list of objects, where each object represents a product. "
            "If no products are found, return an empty list. If you see paragraphs of text, try to separate them into products. "
            "Ignore invoice summary information (e.g., total amount, VAT)."
        )
        response = model.generate_content([img, prompt])
        text = response.text
        if text.strip().startswith("```json"):
            text = text.strip()[7:-3].strip()
        extracted = json.loads(text)
        if not isinstance(extracted, list):
            logger.warning(f"Gemini vision did not return a list: {extracted}")
            return []
        result = []
        for item in extracted:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "name": item.get("name"),
                    "supplier_code": item.get("supplier_code"),
                    "description": item.get("description"),
                    "price": item.get("price"),
                    "currency": item.get("currency", "EUR"),
                    "image_url": item.get("image_url"),
                    "source_file": "",
                }
            )
        return result
    except Exception as e:
        logger.error(f"Gemini vision API call failed: {e}")
        return []


def extract_specifications_from_image(file_path: str) -> List[Dict[str, Any]]:
    """
    Public entry point – extracts specifications from an image file.
    Uses FreeLLMAPI vision model if configured, else Gemini.
    Returns list of dicts with keys: name, supplier_code, description, price, currency, image_url, source_file.
    """
    try:
        with open(file_path, "rb") as f:
            image_bytes = f.read()
    except FileNotFoundError:
        logger.error(f"Image file not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Failed to read image file {file_path}: {e}")
        return []

    if _USE_FREELLM_VISION:
        specs = _extract_with_freellm_vision(image_bytes)
    elif _USE_GEMINI:
        specs = _extract_with_gemini(image_bytes)
    else:
        logger.warning("No vision provider configured; returning empty specs.")
        specs = []

    for s in specs:
        s["source_file"] = file_path
    return specs


def parse_catalog(file_path: str) -> List[Dict[str, Any]]:
    """
    Public entry point – called by the pipeline.
    """
    return extract_specifications_from_image(file_path)


def extract_specifications_from_bytes(image_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract specifications from image bytes.
    Uses FreeLLMAPI vision model if configured, else Gemini.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        try:
            specs = extract_specifications_from_image(tmp_path)
        finally:
            os.unlink(tmp_path)
        return specs
    except Exception as e:
        logger.error(f"Failed to extract specifications from bytes: {e}")
        return []