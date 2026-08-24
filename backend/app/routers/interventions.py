"""
Interventions router — list and manage individual interventions.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models.intervention import Intervention
from app.models.case import Case, CaseStatus
from app.schemas import InterventionResponse

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("/pending", response_model=List[InterventionResponse])
async def list_pending_interventions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """List all interventions awaiting human approval (human_pending cases)."""
    stmt = (
        select(Intervention)
        .join(Case, Intervention.case_id == Case.id)
        .where(Case.status == CaseStatus.human_pending, Case.organization_id == organization.id)
        .order_by(Intervention.scheduled_at.asc())
    )
    result = await db.execute(stmt)
    interventions = result.scalars().all()
    return [InterventionResponse.model_validate(iv) for iv in interventions]


@router.get("/{intervention_id}", response_model=InterventionResponse)
async def get_intervention(
    intervention_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get a single intervention by ID."""
    result = await db.execute(
        select(Intervention).join(Case).where(Intervention.id == intervention_id, Case.organization_id == organization.id)
    )
    iv = result.scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return InterventionResponse.model_validate(iv)
