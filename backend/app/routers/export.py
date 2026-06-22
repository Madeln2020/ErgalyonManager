# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Export Router (Async via Celery)
# Creates a pending ExportJob, delegates generation to background worker.
# ═══════════════════════════════════════════════════════════════════
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ExportJob, Product, ProductSupplierLink, CostUpdate, User, Company, Supplier
from app.routers.auth import get_current_user, require_role
from app.config import settings

router = APIRouter(prefix="/api/v1/export", tags=["Export"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────
class ExportJobRead(BaseModel):
    id: str
    export_type: str
    file_format: str
    status: str
    total_rows: Optional[int]
    object_key: Optional[str]
    error_message: Optional[str] = None
    created_at: Optional[str]
    completed_at: Optional[str] = None


class ExportRequest(BaseModel):
    export_type: str = "products"  # products, costs, suppliers
    file_format: str = "xlsx"      # csv, xlsx, json, xml


# ──────────────────────────────────────────
# GET /jobs — List export jobs
# ──────────────────────────────────────────
@router.get("/jobs", response_model=List[ExportJobRead])
async def list_export_jobs(
    company_id: UUID = Query(..., description="Company tenant ID"),
    db: AsyncSession = Depends(get_db),
):
    """List export jobs for a company."""
    result = await db.execute(
        select(ExportJob)
        .where(ExportJob.company_id == company_id)
        .order_by(ExportJob.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()
    return [
        ExportJobRead(
            id=str(j.id),
            export_type=j.export_type,
            file_format=j.file_format,
            status=j.status,
            total_rows=j.total_rows,
            object_key=j.object_key,
            error_message=j.error_message,
            created_at=str(j.created_at) if j.created_at else None,
            completed_at=str(j.completed_at) if j.completed_at else None,
        )
        for j in jobs
    ]


# ──────────────────────────────────────────
# GET /jobs/{job_id} — Get job status
# ──────────────────────────────────────────
@router.get("/jobs/{job_id}", response_model=ExportJobRead)
async def get_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the status/details of a specific export job."""
    result = await db.execute(
        select(ExportJob).where(ExportJob.id == UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return ExportJobRead(
        id=str(job.id),
        export_type=job.export_type,
        file_format=job.file_format,
        status=job.status,
        total_rows=job.total_rows,
        object_key=job.object_key,
        error_message=job.error_message,
        created_at=str(job.created_at) if job.created_at else None,
        completed_at=str(job.completed_at) if job.completed_at else None,
    )


# ──────────────────────────────────────────
# GET /jobs/{job_id}/download — Download completed export file
# ──────────────────────────────────────────
@router.get("/jobs/{job_id}/download")
async def download_export(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a completed export file."""
    result = await db.execute(
        select(ExportJob).where(ExportJob.id == UUID(job_id))
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export job status is '{job.status}', not 'completed'. "
                   f"Check GET /api/v1/export/jobs/{job_id} for status."
        )
    if not job.object_key or not os.path.isfile(job.object_key):
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    media_map = {
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    media_type = media_map.get(job.file_format, "application/octet-stream")
    filename = f"{job.export_type}_export.{job.file_format}"

    return FileResponse(
        path=job.object_key,
        media_type=media_type,
        filename=filename,
    )


# ──────────────────────────────────────────
# POST / — Create an export job (async via Celery)
# ──────────────────────────────────────────
@router.post("", response_model=ExportJobRead)
async def create_export(
    data: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create an export job. Generation runs in background via Celery.

    Returns immediately with the job (status='pending'). Poll
    GET /api/v1/export/jobs/{job_id} to wait for completion, then
    GET /api/v1/export/jobs/{job_id}/download to retrieve the file.
    """
    # Create the ExportJob record
    job = ExportJob(
        company_id=current_user.company_id,
        export_type=data.export_type,
        file_format=data.file_format,
        status="pending",
        requested_by=current_user.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch Celery background task (fire-and-forget)
    try:
        from celery_worker import generate_export
        generate_export.delay(str(job.id))
    except Exception as exc:
        # If Celery is unavailable, mark as failed gracefully
        job.status = "failed"
        job.error_message = f"Could not launch background worker: {exc}"
        await db.commit()
        logger = __import__("logging").getLogger("edm.export")
        logger.warning("Failed to launch Celery export task for %s: %s", job.id, exc)

    await db.refresh(job)
    return ExportJobRead(
        id=str(job.id),
        export_type=job.export_type,
        file_format=job.file_format,
        status=job.status,
        total_rows=job.total_rows,
        object_key=job.object_key,
        error_message=job.error_message,
        created_at=str(job.created_at) if job.created_at else None,
        completed_at=str(job.completed_at) if job.completed_at else None,
    )
