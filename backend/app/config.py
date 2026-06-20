# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 Backend — Settings (pydantic-settings)
# ═══════════════════════════════════════════════════════════════════
# All environment variables are loaded from .env (local) or
# the container environment (production).
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # ── General ────────────────────────────────────────────────────
    APP_NAME: str = "EDM v2.1"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    HOST: str = "0.0.0.0"
    PORT: int = 8887

    # ── CORS ───────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:8887",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # ── PostgreSQL ─────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://edm:edm_password@localhost:5432/edm_v2"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False  # set True only for debugging SQL

    # ── Redis ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── MinIO / S3-compatible object store ─────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "edm-uploads"
    MINIO_SECURE: bool = False  # True for HTTPS
    MINIO_REGION: str = "us-east-1"

    # ── Security / JWT ─────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # ── File uploads ───────────────────────────────────────────────
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set[str] = {
        ".pdf", ".xml", ".xlsx", ".xls",
        ".csv", ".jpg", ".jpeg", ".png", ".tiff", ".tif",
    }

    # ── Parsing & OCR ──────────────────────────────────────────────
    OCR_LANGUAGE: str = "ell+eng"          # Greek + English
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    PDF_MAX_PAGES: int = 500

    # ── Product Identity (blueprint v2.1 rule) ─────────────────────
    # Product Identity = Supplier Code + Supplier ID (NOT Pylon Code)
    PRODUCT_IDENTITY_USE_PYLON_CODE: bool = False

    # ── Enrichment Order (blueprint v2.1 rule) ─────────────────────
    # Order: XML -> Manual -> Web Scraping (last resort)
    ENRICHMENT_ORDER: list[str] = ["xml", "manual", "web_scrape"]

    # ── Cost Protection (blueprint v2.1 rule) ──────────────────────
    # Existing costs are NEVER overwritten without explicit approval
    COST_PROTECTION_ENABLED: bool = True

    # ── FreeLLM API (primary AI provider for RAG + chat) ──────────
    FREELLM_API_KEY: str = ""
    FREELLM_BASE_URL: str = ""
    FREELLM_EMBEDDING_MODEL: str = "auto"
    FREELLM_CHAT_MODEL: str = "deepseek-ai/deepseek-v4-pro"
    FREELLM_MAX_RETRIES: int = 3
    FREELLM_TIMEOUT: int = 60

    # ── Hermes / AI routing ────────────────────────────────────────
    HERMES_LOCAL_LLM_URL: str = "http://localhost:11434"
    HERMES_PRIVACY_LOCAL_ONLY: bool = True

    # ── Web scraping (last-resort enrichment) ──────────────────────
    CRAWL4AI_TIMEOUT: int = 30
    CRAWL4AI_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # ── Multi-Tenancy (blueprint v2.1) ─────────────────────────────
    # Every table includes a company_id column for logical isolation
    MULTI_TENANCY_ENABLED: bool = True

    # ── Audit Trail (blueprint v2.1) ───────────────────────────────
    # Every change is logged in audit_logs table
    AUDIT_LOG_ENABLED: bool = True

    # ── Poimenidis first test case ─────────────────────────────────
    # Strip "03-" prefix from supplier codes for Poimenidis
    POIMENIDIS_STRIP_03_PREFIX: bool = True

    # ── Ergalyon code format ───────────────────────────────────────
    ERGALYON_CODE_FORMAT: str = "ERG-{seq:08d}"

    # ── Prometheus metrics ─────────────────────────────────────────
    METRICS_ENABLED: bool = True

    # ── model config ───────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
