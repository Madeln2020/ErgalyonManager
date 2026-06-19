"""EDM v2 — Prometheus metrics instrumentation (Phase 4).

Exposes /metrics endpoint and provides decorators/functions to
count HTTP requests, DB query latency, and background job durations.
"""

from functools import wraps
from time import time
from typing import Callable

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# ── HTTP request metrics ─────────────────────────────────────
REQUEST_COUNT = Counter(
    "edm_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "http_status"],
)

REQUEST_LATENCY = Histogram(
    "edm_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# ── Database query metrics ───────────────────────────────────
DB_QUERY_COUNT = Counter(
    "edm_db_queries_total",
    "Total DB queries executed",
    ["query_type", "table"],
)

DB_QUERY_LATENCY = Histogram(
    "edm_db_query_duration_seconds",
    "DB query latency",
    ["query_type", "table"],
)

# ── Background job metrics ───────────────────────────────────
BACKGROUND_JOB_COUNT = Counter(
    "edm_background_jobs_total",
    "Total background jobs processed",
    ["job_type", "status"],
)

BACKGROUND_JOB_LATENCY = Histogram(
    "edm_background_job_duration_seconds",
    "Background job duration",
    ["job_type"],
)


def metrics_endpoint() -> Response:
    """FastAPI endpoint that returns Prometheus metrics."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def track_http_request(method: str, endpoint: str):
    """Decorator to wrap FastAPI endpoint functions."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time()
            try:
                result = await func(*args, **kwargs)
                # Assume success (200) unless exception bubbles up
                status = "200"
                return result
            except Exception as exc:
                # Try to get status code from HTTPException if present
                status = getattr(exc, "status_code", "500")
                raise
            finally:
                elapsed = time() - start
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status).inc()
                REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)

        return wrapper

    return decorator


def track_db_query(query_type: str, table: str):
    """Decorator to wrap DB query functions (e.g. in services)."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time() - start
                DB_QUERY_COUNT.labels(query_type=query_type, table=table).inc()
                DB_QUERY_LATENCY.labels(query_type=query_type, table=table).observe(elapsed)

        return wrapper

    return decorator


def track_background_job(job_type: str, status: str = "success"):
    """Context manager-like decorator for background jobs (Celery tasks)."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time() - start
                BACKGROUND_JOB_COUNT.labels(job_type=job_type, status=status).inc()
                BACKGROUND_JOB_LATENCY.labels(job_type=job_type).observe(elapsed)

        return wrapper

    return decorator
