# EDM v2 Backend — Configuration
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "EDM v2"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8887

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://edm:edm_password@localhost:5432/edm_v2",
    )

    # Redis / Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-insecure-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:8887",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Upload
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # Ergalyon code format
    ERGALYON_CODE_FORMAT: str = "ERG-{seq:08d}"

    # Parsing
    OCR_LANGUAGE: str = "ell+eng"

    # FreeLLM API (replace Gemini for RAG — both embeddings + chat)
    FREELLM_API_KEY: str = ""
    FREELLM_BASE_URL: str = ""
    FREELLM_EMBEDDING_MODEL: str = "auto"
    FREELLM_CHAT_MODEL: str = "deepseek-ai/deepseek-v4-pro"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()