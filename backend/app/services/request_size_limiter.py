"""EDM v2 — Request size limiting middleware (Phase 4).

Rejects requests with Content-Length exceeding the configured limit.
"""

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces a maximum request size."""

    def __init__(self, app, max_size: int = 5 * 1024 * 1024):  # 5 MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        # Get Content-Length header; if missing, we cannot enforce (allow through)
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
                if length > self.max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request entity too large: {length} bytes > {self.max_size} bytes allowed",
                    )
            except ValueError:
                # If header is not a valid integer, let the request proceed (will likely fail later)
                pass

        response = await call_next(request)
        return response


def add_request_size_limit_middleware(app, max_size: int = 5 * 1024 * 1024):
    """Add the request size limit middleware to the FastAPI app."""
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_size)
