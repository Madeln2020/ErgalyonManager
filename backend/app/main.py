# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 Backend — FastAPI Application Entry Point
# ═══════════════════════════════════════════════════════════════════
# CORS, router registration, health endpoint, startup/shutdown events.
# ═══════════════════════════════════════════════════════════════════

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings


# ── Lifespan (startup / shutdown) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle hooks."""
    logger = logging.getLogger("edm")
    logger.info(
        "Starting %s v%s (env: %s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )

    # ── Ensure MinIO bucket exists ──────────────────────────
    try:
        from app.services.minio_client import ensure_bucket_exists
        ensure_bucket_exists()
        logger.info("MinIO bucket 'raw-uploads' ready.")
    except Exception as exc:
        logger.warning("MinIO bucket check failed (non-fatal): %s", exc)

    # ── Initialise connection pools, warm caches, etc. ──────
    yield
    # ── Shutdown: dispose engines, close connections ──────────
    from app.database import engine

    await engine.dispose()
    logger.info("Application shutdown complete.")


# ── FastAPI app instance ───────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Ergalyon Data Manager — Supplier product data pipeline",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)


# ── CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log method, path, status, and duration for every request."""
    start = time.time()
    try:
        response = await call_next(request)
        elapsed = time.time() - start
        logger = logging.getLogger("edm.access")
        logger.info(
            "%s %s → %d (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed * 1000,
        )
        return response
    except Exception as exc:
        elapsed = time.time() - start
        logger = logging.getLogger("edm.access")
        logger.error(
            "%s %s → ERROR (%.2fms): %s",
            request.method,
            request.url.path,
            elapsed * 1000,
            str(exc),
        )
        raise


# ── Health check endpoint ──────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Basic health check — returns app status."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ── Router registration ───────────────────────────────────────────────
# Register all routers as they are implemented
from app.routers import suppliers, products, catalogs, auth, health, upload

app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(catalogs.router)
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(upload.router)


# ── Global exception handler ───────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler returning a structured JSON error."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "path": request.url.path,
            }
        },
    )
