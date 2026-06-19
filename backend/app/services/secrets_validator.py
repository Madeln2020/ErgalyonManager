"""
EDM v2 — Secrets & Configuration Validation (Phase 5).

Validates that all required secrets and configuration values are present
at startup.  Exits early with a clear error message if anything is
missing, preventing half‑configured application states.

Add a ``SECRETS_WHITELIST`` to the environment (comma‑separated) to
explicitly allow secret names.
"""

import os
import sys
import logging
from typing import List, Optional

logger = logging.getLogger("edm.secrets_validator")

# ── Required secrets for production ────────────────────────────────
# These must have non‑default values in production mode.
PRODUCTION_REQUIRED_SECRETS = {
    "SECRET_KEY": "Application encryption key (min 32 chars). Generate with: openssl rand -hex 32",
    "DATABASE_URL": "PostgreSQL connection string",
    "REDIS_URL": "Redis connection string (used for caching, Celery, rate limiting)",
}

# ── Optional but strongly recommended ──────────────────────────────
RECOMMENDED_SECRETS = {
    "GOOGLE_APPLICATION_CREDENTIALS": "Google Cloud Vision / Vertex AI credentials file path",
    "GOOGLE_API_KEY": "Google Gemini API key (for vision catalog parser)",
    "SENTRY_DSN": "Sentry error tracking DSN (if Sentry is configured)",
}

# ── Default values that should NEVER be used in production ─────────
INSECURE_DEFAULTS = {
    "SECRET_KEY": "dev-insecure-change-in-production",
    "DATABASE_URL": "postgresql+asyncpg://edm:edm_password@localhost:5432/edm_v2",
    "REDIS_URL": "redis://localhost:6379/0",
}


def check_secrets(environment: str = "development") -> List[str]:
    """Validate secrets and return a list of issues.

    In production mode, fails hard on missing required secrets.
    In development mode, logs warnings.

    Parameters
    ----------
    environment:
        ``"development"`` or ``"production"``.  Controlled by
        the ``ENVIRONMENT`` setting.
    """
    issues: List[str] = []

    # 1) Check required secrets in production
    if environment == "production":
        for secret, description in PRODUCTION_REQUIRED_SECRETS.items():
            value = os.getenv(secret, "")
            if not value:
                issues.append(f"MISSING: {secret} — {description}")
            elif value in INSECURE_DEFAULTS.get(secret, ""):
                issues.append(f"INSECURE: {secret} still uses the default value! {description}")

    # 2) Check for insecure defaults regardless of environment
    for secret, default_value in INSECURE_DEFAULTS.items():
        value = os.getenv(secret, "")
        if value == default_value:
            issues.append(f"WARNING: {secret} uses insecure default value. {PRODUCTION_REQUIRED_SECRETS.get(secret, 'Change before deploying to production.')}")

    # 3) Check SECRET_KEY length in production
    if environment == "production":
        secret_key = os.getenv("SECRET_KEY", "")
        if secret_key and len(secret_key) < 32:
            issues.append(f"WEAK: SECRET_KEY is only {len(secret_key)} characters. Minimum recommended: 32.")

    return issues


def validate_and_exit(environment: str = "development") -> None:
    """Run validation and exit with a clear error if issues found.

    Call this during application startup *after* logging is configured.
    """
    issues = check_secrets(environment)

    if not issues:
        logger.info("Secrets validation passed")
        return

    for issue in issues:
        if issue.startswith("MISSING") or issue.startswith("INSECURE"):
            logger.error("SECRETS VALIDATION: %s", issue)
        else:
            logger.warning("SECRETS VALIDATION: %s", issue)

    # Fatal issues in production
    fatal = [i for i in issues if i.startswith("MISSING") or i.startswith("INSECURE")]
    if fatal and environment == "production":
        logger.critical("FATAL: %d secrets validation errors — aborting startup", len(fatal))
        sys.exit(1)
