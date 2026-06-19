"""EDM v2 — Audit trail service (§4 Observability / Event Audit).

Provides a lightweight ``log_event`` function that persists lifecycle
events to the ``audit_log`` table.  Every mutation to core entities
(suppliers, products, invoices, review queue) should call this so we
have a complete, queryable history of what changed, when, and by whom.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import AuditLog

logger = logging.getLogger("edm.audit")


async def log_event(
    entity_type: str,
    entity_id: UUID,
    event_name: str,
    user_id: Optional[UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
    session: Optional[AsyncSession] = None,
) -> bool:
    """Persist one audit event to the database.

    Parameters
    ----------
    entity_type:
        Domain entity, e.g. ``"supplier"``, ``"product"``, ``"invoice"``,
        ``"review_queue"``, ``"supplier_rule"``.
    entity_id:
        UUID of the affected entity.
    event_name:
        Short human‑readable verb, e.g. ``"created"``, ``"updated"``,
        ``"deleted"``, ``"approved"``, ``"rejected"``, ``"uploaded"``.
    user_id:
        Optional UUID of the user / system that initiated the change.
    payload:
        Optional JSON-serialisable dict with details (old/new values, etc).
    session:
        Optional existing DB session.  If omitted, a new session is created
        and committed.

    Returns
    -------
    ``True`` on success, ``False`` on failure (logged as error).
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        event_name=event_name,
        user_id=user_id,
        payload=payload or {},
        created_at=datetime.now(timezone.utc),
    )

    own_session = session is None
    if own_session:
        session_instance = async_session_factory()
    else:
        session_instance = session

    try:
        session_instance.add(entry)
        if own_session:
            await session_instance.commit()
        else:
            await session_instance.flush()
        logger.info("Audit: %s %s %s", event_name, entity_type, entity_id)
        return True
    except Exception as exc:
        logger.error("Audit log failed for %s %s: %s", event_name, entity_id, exc)
        if own_session:
            await session_instance.rollback()
        return False
    finally:
        if own_session:
            await session_instance.close()
