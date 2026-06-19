# EDM v2 Backend — Main Application Entry Point

from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.database import engine, Base
from app.services.logging_config import setup_logging
from app.services.metrics import metrics_endpoint, REQUEST_COUNT, REQUEST_LATENCY, track_http_request
from app.services.rate_limiter import add_rate_limiting_middleware
from app.services.request_size_limiter import add_request_size_limit_middleware
from app.services.input_sanitizer import add_input_sanitization_middleware
from app.services.secrets_validator import validate_and_exit

from sqlalchemy import text
from app.routers import suppliers, products, invoices, review_queue, export, rules, catalogs, rag, scrape, supplier_agreements, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup if they don't exist (dev mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Setup structured logging
log_level = getattr(settings, "LOG_LEVEL", "INFO")
setup_logging(log_level)

# Validate secrets on startup (warns in dev, exits in production)
validate_and_exit(environment=settings.ENVIRONMENT)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input sanitization middleware (protect against XSS/injection)
add_input_sanitization_middleware(app)

# Request size limit middleware (reject overly large payloads)
add_request_size_limit_middleware(app, max_size=10 * 1024 * 1024)  # 10 MB default

# HTTP request logging & metrics middleware
@app.middleware("http")
async def logging_and_metrics_middleware(request: Request, call_next):
    """Log request/response and collect Prometheus metrics."""
    start_time = time.time()
    method = request.method
    path = request.url.path
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        # Structured log (JSON via logging_config)
        logger = logging.getLogger("edm.access")
        logger.info(
            "HTTP request processed",
            extra={
                "extra_json": {
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                    "client_ip": request.client.host if request.client else None,
                }
            },
        )
        # Prometheus metrics
        REQUEST_COUNT.labels(method=method, endpoint=path, http_status=str(response.status_code)).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(process_time)
        return response
    except Exception as exc:
        process_time = time.time() - start_time
        # Determine status code from exception if it's an HTTPException
        status_code = getattr(exc, "status_code", 500)
        # Structured log (JSON via logging_config) for failed requests
        logger = logging.getLogger("edm.access")
        logger.error(
            "HTTP request failed",
            extra={
                "extra_json": {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                    "client_ip": request.client.host if request.client else None,
                    "exception": str(exc),
                }
            },
        )
        # Prometheus metrics for failed requests (we still count them)
        REQUEST_COUNT.labels(method=method, endpoint=path, http_status=str(status_code)).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(process_time)
        raise

# Rate limiting middleware
add_rate_limiting_middleware(app)



# Prometheus metrics endpoint
app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

# Routers
app.include_router(suppliers.router)
app.include_router(catalogs.router)
app.include_router(products.router)
app.include_router(invoices.router)
app.include_router(review_queue.router)
app.include_router(export.router)
app.include_router(rules.router)
app.include_router(scrape.router)
app.include_router(supplier_agreements.router)

app.include_router(rag.router)
app.include_router(health.router)


async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "request_id": None,
            }
        },
    )
