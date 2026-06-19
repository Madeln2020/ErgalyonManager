"""EDM v2 — Health router with DB and Redis checks."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from app.database import async_session_factory
from app.services.cache import _get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check endpoint verifying DB and Redis connectivity."""
    db_status = "ok"
    db_error = None
    try:
        # Simple DB connectivity check
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)
    redis_status = "ok"
    redis_error = None
    try:
        r = _get_redis()
        if r is not None:
            r.ping()  # sync client — no await
        else:
            redis_status = "warning"
            redis_error = "Redis client not initialized"
    except Exception as e:
        redis_status = "error"
        redis_error = str(e)
    overall = "ok" if db_status == "ok" and redis_status in ("ok", "warning") else "error"
    return {
        "status": overall,
        "version": "0.1.0",  # TODO: pull from settings
        "checks": {
            "database": {"status": db_status, "error": db_error},
            "redis": {"status": redis_status, "error": redis_error},
        },
    }
