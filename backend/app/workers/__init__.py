# EDM v2 — Celery Worker Configuration (§4)

from celery import Celery

from app.config import settings

celery_app = Celery(
    "edm_v2",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Athens",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3)
def health_check(self):
    return {"status": "ok", "worker": "edm_v2"}


@celery_app.task(bind=True, max_retries=3)
def process_invoice(self, invoice_id: str):
    """Async task: parse, normalize, enrich invoice."""
    return {"invoice_id": invoice_id, "status": "queued"}
