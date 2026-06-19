from __future__ import annotations
import os
from celery import Celery
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.rag_service import RAGService
from app.config import settings

# Celery configuration – use Redis broker (already a dependency)
celery_app = Celery(
    "edm_v2_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Async DB session factory (reuse same settings as app)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@celery_app.task(name="enrich_product")
async def enrich_product_task(product_id: str, context: str):
    async with AsyncSessionLocal() as db:
        service = RAGService(db)
        await service.enrich(product_id, context)
        return {"status": "ok", "product_id": product_id}

if __name__ == "__main__":
    celery_app.start()
