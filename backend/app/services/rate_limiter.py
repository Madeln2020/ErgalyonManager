"""EDM v2 — Rate limiting middleware (Phase 4).

Uses Redis to implement a fixed-window counter per IP and endpoint.
"""

import time
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.cache import _get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that adds rate limiting based on Redis."""

    def __init__(
        self,
        app,
        requests_per_window: int = 10,
        window_seconds: int = 60,
        exempt_paths: list[str] | None = None,
        exempt_ips: list[str] | None = None,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or []
        self.exempt_ips = exempt_ips or ["127.0.0.1", "::1"]  # exempt localhost
        self.redis = _get_redis()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if Redis is not available
        if self.redis is None:
            return await call_next(request)

        # Skip if path is exempt
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip if client IP is exempt
        client_host = request.client.host if request.client else None
        if client_host in self.exempt_ips:
            return await call_next(request)

        # Create a key for this IP and endpoint
        # We'll use the path and method to differentiate endpoints
        key = f"rate_limit:{client_host}:{request.method}:{request.url.path}"
        window = int(time.time() // self.window_seconds)
        key_with_window = f"{key}:{window}"

        # Increment the counter
        try:
            current = self.redis.incr(key_with_window)
            if current == 1:
                # Set expiry for the window
                self.redis.expire(key_with_window, self.window_seconds)
        except Exception:
            # If Redis fails, we allow the request to proceed (fail open)
            return await call_next(request)

        # Check if we exceeded the limit
        if current > self.requests_per_window:
            # Calculate retry-after seconds
            ttl = self.redis.ttl(key_with_window)
            retry_after = ttl if ttl > 0 else self.window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def add_rate_limiting_middleware(app):
    """Add the rate limiting middleware to the FastAPI app."""
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=10,
        window_seconds=60,
        exempt_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/health",
        ],  # exempt docs and metrics
        exempt_ips=["127.0.0.1", "::1"],
    )
