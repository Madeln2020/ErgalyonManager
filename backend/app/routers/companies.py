# ═══════════════════════════════════════════════════════════════════
# EDM v2.1 — Company Router (Multi-tenancy management)
# ═══════════════════════════════════════════════════════════════════
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Company
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


# ── Pydantic schemas ──────────────────────────────────────────────
class CompanyCreate(BaseModel):
    name: str
    vat_number: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    vat_number: Optional[str] = None


class CompanyRead(BaseModel):
    id: str
    name: str
    vat_number: Optional[str]
    created_at: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────
@router.get("", response_model=list[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Company).where(Company.is_active == True))
    companies = result.scalars().all()
    return [CompanyRead(
        id=str(c.id), name=c.name, vat_number=c.vat_number,
        created_at=str(c.created_at) if c.created_at else None
    ) for c in companies]


@router.post("", response_model=CompanyRead)
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    company = Company(name=data.name, vat_number=data.vat_number)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return CompanyRead(
        id=str(company.id), name=company.name, vat_number=company.vat_number,
        created_at=str(company.created_at) if company.created_at else None
    )
