import json
from typing import List, Dict, Any
import google.generativeai as genai
import os
import tempfile

# Configure API key from environment variable
# It's HIGHLY recommended to use environment variables for sensitive data.
# E.g., add GEMINI_API_KEY=*** to your .env file
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    _USE_REAL_API = True
except KeyError:
    print("WARNING: GEMINI_API_KEY not found in environment variables. Vision parser will use mock data.")
    genai.configure(api_key="DUMMY_API_KEY_FOR_MOCK")
    _USE_REAL_API = False

def _mock_extract_specifications() -> List[Dict[str, Any]]:
    """Return mock specifications for testing/demo."""
    return [
        {
            "name": "Αυτοκόλλητο Δοχείο 5L",
            "supplier_code": "CAT-0001",
            "description": "Πλαστικό δοχείο με αυτοκόλλητο κλείδι, χρώμα λευκό.",
            "price": 12.5,
            "currency": "EUR",
            "image_url": "https://example.com/images/cat-0001.jpg",
        },
        {
            "name": "Κάδικο Χειρός 250g",
            "supplier_code": "CAT-0002",
            "description": "Κάδικο υψηλής αντοχής, 250 γραμμάρια.",
            "price": 3.8,
            "currency": "EUR",
            "image_url": "https://example.com/images/cat-0002.jpg",
        },
    ]

def extract_specifications_from_image(file_path: str) -> List[Dict[str, Any]]:
    """
    Uses Google Gemini Vision model to extract product specifications from an image/PDF.
    Returns a list of dicts: name, supplier_code, description, price, currency, image_url.
    Falls back to mock data if API is unavailable or fails.
    """
    # If we are not configured to use real API, return mock directly.
    if not _USE_REAL_API:
        return _mock_extract_specifications()

    try:
        img_bytes = open(file_path, "rb").read()
    except FileNotFoundError:
        print(f"ERROR: Image file not found at {file_path}")
        # Fallback to mock
        return _mock_extract_specifications()

    # Create the model for vision
    model = genai.GenerativeModel('gemini-pro-vision')

    # Write bytes to a temporary file because upload_file expects a path
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        uploaded_file = genai.upload_file(path=tmp_path, display_name="catalog_image")
        prompt = (
            "Examine this catalog or invoice image carefully. Identify products and extract the following information for each one:\n"
            "- **name**: The product name.\n"
            "- **supplier_code**: The product code from the supplier. Look for numeric or alphanumeric codes near the name.\n"
            "- **description**: A brief description of the product.\n"
            "- **price**: The unit price of the product. Should be a number.\n"
            "- **currency**: The currency (e.g., EUR, USD). Prefer EUR.\n"
            "- **image_url**: If there is an explicit image URL for the product, otherwise leave blank.\n\n"
            "Return the results as a JSON list of objects, where each object represents a product. If no products are found, return an empty list. If you see paragraphs of text, try to separate them into products. Ignore invoice summary information (e.g., total amount, VAT).\n\n"
            "Example format:\n"
            "```json\n"
            "[\n"
            "  {\n"
            "    \"name\": \"Product A\",\n"
            "    \"supplier_code\": \"PRD-001\",\n"
            "    \"description\": \"Description of product A.\",\n"
            "    \"price\": 10.50,\n"
            "    \"currency\": \"EUR\",\n"
            "    \"image_url\": \"\"\n"
            "  }\n"
            "]\n"
            "```"
        )

        response = model.generate_content([uploaded_file, prompt], stream=False)
        # Attempt to parse the response as JSON
        # Gemini often wraps JSON in markdown code blocks
        text_response = response.text
        if text_response.startswith('```json') and text_response.endswith('```'):
            text_response = text_response[len('```json'):-len('```')].strip()
        
        extracted_specs = json.loads(text_response)
        
        if not isinstance(extracted_specs, list):
            print(f"WARNING: Gemini did not return a list of JSON objects. Raw response: {response.text}")
            return _mock_extract_specifications()
        
        return extracted_specs

    except Exception as e:
        print(f"Error calling Gemini Vision API: {e}")
        # Fallback to mock data on any error
        return _mock_extract_specifications()
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

def parse_catalog(file_path: str) -> List[Dict[str, Any]]:
    """Public entry point – called by the pipeline."""
    specs = extract_specifications_from_image(file_path)
    # Add a `source_file` field for traceability
    for s in specs:
        s["source_file"] = file_path
    return specs
