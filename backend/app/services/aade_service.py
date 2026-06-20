# EDM v2.1 — AADE Integration Service
# Mock AADE API that fetches tax profile data for Greek AFM (vat_number)

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any

logger = logging.getLogger("edm.aade")


# Simulated AADE tax profile data
# In production, this would call the actual AADE API (myDATA)
_MOCK_AADE_DATA: dict[str, dict[str, Any]] = {
    "800000001": {
        "taxpayer_name": "POIMENIDIS S.A.",
        "tax_office": "Α' ΑΘΗΝΩΝ",
        "activity_code": "46.49.19—",
        "activity_description": "ΧΟΝΔΡΙΚΟ ΕΜΠΟΡΙΟ ΑΛΛΩΝ ΜΗΧΑΝΗΜΑΤΩΝ",
        "registration_date": "1995-03-15",
        "legal_form": "ΑΝΩΝΥΜΗ ΕΤΑΙΡΕΙΑ",
        "address": {
            "street": "ΛΕΩΦ. ΑΘΗΝΩΝ 125",
            "postal_code": "10445",
            "city": "ΑΘΗΝΑ",
            "region": "ΑΤΤΙΚΗΣ",
        },
        "contact": {
            "phone": "+302101234567",
            "email": "info@poimenidis.gr",
            "website": "https://www.poimenidis.gr",
        },
        "vat_status": "active",
        "gemi_number": "123456789",
    },
    "999999999": {
        "taxpayer_name": "DEMO SUPPLIER Ε.Ε.",
        "tax_office": "Β' ΘΕΣΣΑΛΟΝΙΚΗΣ",
        "activity_code": "46.63.00—",
        "activity_description": "ΧΟΝΔΡΙΚΟ ΕΜΠΟΡΙΟ ΜΗΧΑΝΗΜΑΤΩΝ",
        "registration_date": "2010-06-01",
        "legal_form": "ΕΤΕΡΟΡΡΥΘΜΗ ΕΤΑΙΡΕΙΑ",
        "address": {
            "street": "ΒΕΝΙΖΕΛΟΥ 45",
            "postal_code": "54625",
            "city": "ΘΕΣΣΑΛΟΝΙΚΗ",
            "region": "ΚΕΝΤΡΙΚΗΣ ΜΑΚΕΔΟΝΙΑΣ",
        },
        "contact": {
            "phone": "+302310876543",
            "email": "sales@demosupplier.gr",
        },
        "vat_status": "active",
        "gemi_number": "987654321",
    },
}


def _mock_aade_hash(vat_number: str) -> str:
    """Simulate AADE API response hash for caching."""
    return hashlib.md5(f"aade_{vat_number}".encode()).hexdigest()


async def fetch_tax_profile_from_aade(
    vat_number: str, *, timeout: float = 5.0
) -> Optional[dict]:
    """Fetch tax profile from AADE (mock implementation).

    Args:
        vat_number: Greek AFM (9 digits, validated format)
        timeout: Max seconds to wait for response

    Returns:
        Dict with tax_profile_json data, or None if not found / timeout.
    """
    # Validate format (basic check)
    clean_vat = vat_number.strip().replace("-", "").replace(" ", "")
    if not clean_vat.isdigit() or len(clean_vat) != 9:
        logger.warning("Invalid Greek AFM format: %s", vat_number)
        return None

    logger.info("Fetching AADE tax profile for AFM: %s", clean_vat)

    # Simulate network latency
    await asyncio.sleep(0.3)

    # Look up in mock data
    result = _MOCK_AADE_DATA.get(clean_vat)
    if result:
        logger.info(
            "AADE profile found for %s: %s",
            clean_vat,
            result.get("taxpayer_name", "UNKNOWN"),
        )
    else:
        logger.info("No AADE profile found for AFM: %s", clean_vat)

    return result


async def fetch_tax_profile_for_supplier(vat_number: str) -> Optional[dict]:
    """Fetch AADE profile, or return generated mock data for unknown AFMs.

    In production, you'd only return data from actual AADE responses.
    """
    profile = await fetch_tax_profile_from_aade(vat_number)

    if not profile:
        # In production, return None and let the frontend display "not found"
        # For EDM v2.1, generate synthetic data for testing
        profile = {
            "taxpayer_name": f"SUPPLIER-{vat_number[-4:]}",
            "vat_status": "unknown",
            "registration_date": "2020-01-01",
            "address": {
                "postal_code": f"{vat_number[:5]}",
                "city": "UNKNOWN",
            },
            "contact": {},
        }

    profile["aade_fetched_at"] = datetime.now(timezone.utc).isoformat()
    return profile