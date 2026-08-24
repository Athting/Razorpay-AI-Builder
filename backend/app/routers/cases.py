"""
Cases router — List, filter, detail, and HITL approval endpoints.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models import Case, Customer, Diagnosis, Intervention, Outcome
from app.models.case import CaseStatus, CaseType
from app.models.audit_log import AuditActor
from app.schemas import (
    PaginatedCases, CaseListItem, CaseDetail,
    CustomerResponse, DiagnosisResponse, InterventionResponse, OutcomeResponse,
)
from app.services.audit_service import append as audit_append

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=PaginatedCases)
async def list_cases(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    root_cause: Optional[str] = Query(None),
    min_amount: Optional[int] = Query(None),
    max_amount: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """List all cases with filters and pagination."""
    stmt = (
        select(Case)
        .options(
            selectinload(Case.customer),
            selectinload(Case.diagnoses),
            selectinload(Case.interventions),
        )
        .order_by(Case.opened_at.desc())
        .where(Case.organization_id == organization.id)
    )

    # Apply filters
    filters = []
    if type:
        try:
            filters.append(Case.type == CaseType(type))
        except ValueError:
            pass
    if status:
        try:
            filters.append(Case.status == CaseStatus(status))
        except ValueError:
            pass
    if min_amount:
        filters.append(Case.amount_at_risk >= min_amount)
    if max_amount:
        filters.append(Case.amount_at_risk <= max_amount)

    if filters:
        stmt = stmt.where(and_(*filters))

    # Search by customer name/email (join required)
    if search:
        stmt = stmt.join(Customer).where(
            or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Paginate
    offset = (page - 1) * size
    stmt = stmt.offset(offset).limit(size)
    result = await db.execute(stmt)
    cases = result.scalars().all()

    # Filter by root_cause (in Python since diagnosis is separate table)
    if root_cause:
        cases = [c for c in cases if c.diagnoses and
                 any(d.root_cause == root_cause for d in c.diagnoses)]

    items = []
    for c in cases:
        latest_diag = c.diagnoses[-1] if c.diagnoses else None
        items.append(CaseListItem(
            id=c.id,
            customer_id=c.customer_id,
            customer=CustomerResponse(
                id=c.customer.id,
                name=c.customer.name,
                email=c.customer.email,
                phone=c.customer.phone,
                segment=c.customer.segment,
                risk_score=c.customer.risk_score,
                dnd_opt_out=c.customer.dnd_opt_out,
                channel_opts=c.customer.channel_opts,
                city=c.customer.city,
                created_at=c.customer.created_at,
                tenure_days=c.customer.tenure_days,
            ) if c.customer else None,
            type=c.type,
            status=c.status,
            amount_at_risk=c.amount_at_risk,
            recovered_amount=c.recovered_amount,
            opened_at=c.opened_at,
            closed_at=c.closed_at,
            days_open=c.days_open,
            attempt_count=len(c.interventions),
            latest_root_cause=latest_diag.root_cause if latest_diag else None,
            latest_confidence=latest_diag.confidence if latest_diag else None,
        ))

    return PaginatedCases(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get full case detail with timeline."""
    stmt = (
        select(Case)
        .options(
            selectinload(Case.customer),
            selectinload(Case.diagnoses),
            selectinload(Case.interventions),
            selectinload(Case.outcomes),
        )
        .where(Case.id == case_id, Case.organization_id == organization.id)
    )
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    latest_diag = case.diagnoses[-1] if case.diagnoses else None

    return CaseDetail(
        id=case.id,
        customer_id=case.customer_id,
        customer=CustomerResponse(
            id=case.customer.id,
            name=case.customer.name,
            email=case.customer.email,
            phone=case.customer.phone,
            segment=case.customer.segment,
            risk_score=case.customer.risk_score,
            dnd_opt_out=case.customer.dnd_opt_out,
            channel_opts=case.customer.channel_opts,
            city=case.customer.city,
            created_at=case.customer.created_at,
            tenure_days=case.customer.tenure_days,
        ) if case.customer else None,
        type=case.type,
        status=case.status,
        amount_at_risk=case.amount_at_risk,
        recovered_amount=case.recovered_amount,
        opened_at=case.opened_at,
        closed_at=case.closed_at,
        days_open=case.days_open,
        attempt_count=len(case.interventions),
        latest_root_cause=latest_diag.root_cause if latest_diag else None,
        latest_confidence=latest_diag.confidence if latest_diag else None,
        diagnoses=[DiagnosisResponse.model_validate(d) for d in case.diagnoses],
        interventions=[InterventionResponse.model_validate(i) for i in case.interventions],
        outcomes=[OutcomeResponse.model_validate(o) for o in case.outcomes],
    )


@router.post("/{case_id}/approve")
async def approve_case_action(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Human approves the pending intervention for a case (HITL gate)."""
    result = await db.execute(
        select(Intervention)
        .where(and_(
            Intervention.case_id == case_id,
            Intervention.approved_by_human == False,
            Intervention.executed_at.is_(None),
        ))
        .join(Case).where(Case.organization_id == organization.id)
        .order_by(Intervention.scheduled_at.desc())
    )
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail="No pending intervention found")

    intervention.approved_by_human = True
    await db.flush()

    await audit_append(
        db=db,
        actor=AuditActor.human,
        action="intervention_approved",
        reasoning=f"Human agent {current_user.email} approved {intervention.action_type.value} intervention.",
        case_id=case_id,
    )
    await db.commit()

    # Queue execution
    from app.workers.execution_worker import execute_intervention
    execute_intervention.apply_async(args=[str(intervention.id)], queue="execution")

    return {"status": "approved", "intervention_id": str(intervention.id)}


@router.post("/{case_id}/reject")
async def reject_case_action(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Human rejects the pending intervention — re-run policy engine for next best action."""
    result = await db.execute(
        select(Intervention)
        .where(and_(
            Intervention.case_id == case_id,
            Intervention.approved_by_human == False,
            Intervention.executed_at.is_(None),
        ))
        .join(Case).where(Case.organization_id == organization.id)
        .order_by(Intervention.scheduled_at.desc())
    )
    intervention = result.scalar_one_or_none()
    if not intervention:
        raise HTTPException(status_code=404, detail="No pending intervention found")

    from app.models.intervention import InterventionResult
    intervention.result = InterventionResult.failed
    intervention.executed_at = intervention.scheduled_at

    result2 = await db.execute(select(Case).where(Case.id == case_id, Case.organization_id == organization.id))
    case = result2.scalar_one_or_none()
    if case:
        case.status = CaseStatus.in_progress

    await audit_append(
        db=db,
        actor=AuditActor.human,
        action="intervention_rejected",
        reasoning=f"Human agent {current_user.email} rejected {intervention.action_type.value}. Re-running policy engine.",
        case_id=case_id,
    )
    await db.commit()

    # Re-run policy
    from app.workers.policy_worker import run_policy
    run_policy.apply_async(args=[str(case_id)], queue="policy")

    return {"status": "rejected", "message": "Policy engine re-running"}


@router.post("/{case_id}/escalate")
async def escalate_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Manually escalate a case to human agent."""
    result = await db.execute(select(Case).where(Case.id == case_id, Case.organization_id == organization.id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = CaseStatus.human_pending
    await audit_append(
        db=db,
        actor=AuditActor.human,
        action="manually_escalated",
        reasoning=f"Case manually escalated by {current_user.email}.",
        case_id=case_id,
    )
    await db.commit()
    return {"status": "escalated"}
