# EDM v2 — Audit trail service (§4 Observability / Event Audit)
# Provides a lightweight log_event function that persists lifecycle events to the audit_log table.

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import AuditLog

logger = logging.getLogger("edm.audit")


def _convert_to_json_serializable(obj: Any) -> Any:
    """Recursively convert UUID and Decimal objects to JSON-serializable values."""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, Decimal):
        # Convert to float for JSON; note: may lose precision, but acceptable for audit
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_json_serializable(v) for v in obj]
    else:
        return obj


async def log_event(
    entity_type: str,
    entity_id: UUID,
    event_name: str,
    company_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    payload: Optional[Dict[str, Any]] = None,
    session: Optional[AsyncSession] = None,
) -> bool:
    """Persist one audit event to the database."""
    # Convert UUIDs and Decimals in payload to JSON-serializable values
    safe_payload = _convert_to_json_serializable(payload) if payload else None

    if company_id is None:
        company_id = UUID("00000000-0000-0000-0000-000000000001")

    entry = AuditLog(
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=event_name,
        payload_json=safe_payload or {},
        user_id=user_id,
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