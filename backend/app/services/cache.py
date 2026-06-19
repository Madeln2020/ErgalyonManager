"""EDM v2 — Redis caching utilities for Phase 4 optimization.

Provides a simple cache‑aside pattern using Redis.  Functions return
cached JSON when available and populate the cache on miss.
"""

import json
import hashlib
from typing import Any, Optional

import redis
from app.config import settings

# Lazy Redis client – created on first use so the app still boots when
# Redis is unavailable (graceful degradation).
_redis: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        try:
            _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis.ping()  # verify connection
        except Exception:
            # If Redis is down we simply skip caching.
            _redis = None
    return _redis  # type: ignore[return-value]


def make_key(prefix: str, *args: Any) -> str:
    """Deterministic cache key from a prefix + arbitrary args."""
    raw = ":".join(str(a) for a in args)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"edm:{prefix}:{h}"


def get_cached(key: str) -> Optional[dict]:
    """Return cached dict or None on miss / Redis unavailable."""
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception:
        pass
    return None


def set_cached(key: str, value: Any, ttl: int = 120) -> None:
    """Store a JSON-serializable value in Redis with TTL (default 2 minutes)."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def invalidate(prefix: str, *args: Any) -> None:
    """Delete a cached key."""
    r = _get_redis()
    if r is None:
        return
    key = make_key(prefix, *args)
    try:
        r.delete(key)
    except Exception:
        pass
