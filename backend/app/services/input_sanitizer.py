"""
EDM v2 — Input Sanitization & Validation (Phase 5: Production Hardening).

Provides middleware and utility functions to sanitize and validate
incoming request data. Protects against XSS, SQL injection patterns,
and excessively long inputs.
"""

import html
import re
import logging
from typing import Any, Dict, Optional

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("edm.sanitizer")

# ── Dangerous pattern detection ────────────────────────────────────
# Patterns commonly used in XSS / injection attacks
_DANGEROUS_PATTERNS = re.compile(
    r"(?:<script[^>]*>|</script>|javascript\s*:|on\w+\s*=|"
    r"\b(?:ALTER|CREATE|DROP|TRUNCATE|INSERT|DELETE|UPDATE|EXEC|UNION|"
    r"SELECT\s+.*?\s+FROM|LOAD_FILE|INTO\s+OUTFILE|"
    r"xp_cmdshell|sp_executesql|pg_sleep|SLEEP\s*\())",
    re.IGNORECASE,
)

# Maximum string length for various fields
MAX_STRING_LENGTH = 5000
MAX_SHORT_STRING = 255
MAX_CODE_STRING = 100


def sanitize_string(value: str, max_length: int = MAX_STRING_LENGTH) -> str:
    """Sanitize a single string value.

    - Truncates to *max_length*
    - HTML‑escapes dangerous characters
    - Strips leading/trailing whitespace
    """
    value = value.strip()
    if len(value) > max_length:
        value = value[:max_length]
        logger.warning("String truncated to %d chars", max_length)
    return html.escape(value, quote=True)


def contains_dangerous_patterns(value: str) -> bool:
    """Return True if *value* contains XSS / SQL injection patterns."""
    return bool(_DANGEROUS_PATTERNS.search(value))


def sanitize_dict(
    data: Dict[str, Any],
    max_length: int = MAX_STRING_LENGTH,
    allow_html: Optional[set] = None,
) -> Dict[str, Any]:
    """Recursively sanitize string values in a dictionary.

    Parameters
    ----------
    data:
        The input dict (typically from request body).
    max_length:
        Max allowed length for string values.
    allow_html:
        Optional set of field names that are allowed to contain HTML
        (e.g. rendered descriptions).  These fields are still truncated
        but not HTML‑escaped.

    Returns
    -------
    Cleaned dict (in‑place modified).
    """
    allow_html = allow_html or set()
    for key, value in data.items():
        if isinstance(value, str):
            if contains_dangerous_patterns(value):
                logger.warning("Dangerous pattern detected in field '%s', sanitizing", key)
                value = _DANGEROUS_PATTERNS.sub("", value)
            if key not in allow_html and not value.startswith("data:"):
                value = sanitize_string(value, max_length)
            else:
                # Truncate only, keep HTML
                if len(value) > max_length:
                    value = value[:max_length]
            data[key] = value
        elif isinstance(value, dict):
            sanitize_dict(value, max_length, allow_html)
        elif isinstance(value, list):
            data[key] = [
                sanitize_dict(v, max_length, allow_html) if isinstance(v, dict)
                else sanitize_string(v, max_length) if isinstance(v, str)
                else v
                for v in value
            ]
    return data


# ── Middleware ──────────────────────────────────────────────────────

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware that sanitizes JSON request bodies.

    Scans for dangerous patterns (XSS/SQL injection) and truncates
    excessively long strings.  Skips endpoints that intentionally accept
    raw data (uploads, binary files).
    """

    # Paths that should NOT be sanitized (file uploads, binary data)
    SKIP_PATHS: set = {"/api/v1/invoices/upload", "/api/v1/catalogs/upload",
                       "/api/v1/supplier-agreements/upload",
                       "/metrics", "/health", "/docs", "/redoc", "/openapi.json"}

    def __init__(self, app, max_string_length: int = MAX_STRING_LENGTH):
        super().__init__(app)
        self.max_string_length = max_string_length

    async def dispatch(self, request: Request, call_next):
        # Skip non‑JSON and upload paths
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        for skip in self.SKIP_PATHS:
            if path == skip or path.startswith(skip):
                return await call_next(request)

        # Read body, sanitize, replace
        try:
            body_bytes = await request.body()
            if not body_bytes:
                return await call_next(request)

            import json
            try:
                body_dict = json.loads(body_bytes)
                if isinstance(body_dict, dict):
                    sanitized = sanitize_dict(body_dict, self.max_string_length)
                    # Re‑encode the sanitized body
                    sanitized_bytes = json.dumps(sanitized).encode("utf-8")
                    request._body = sanitized_bytes  # type: ignore[attr-defined]
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Not valid JSON – pass through
        except Exception as exc:
            logger.error("Sanitization middleware error: %s", exc)

        return await call_next(request)


def add_input_sanitization_middleware(app, max_string_length: int = MAX_STRING_LENGTH):
    """Add input sanitization middleware to the FastAPI app."""
    app.add_middleware(InputSanitizationMiddleware, max_string_length=max_string_length)
