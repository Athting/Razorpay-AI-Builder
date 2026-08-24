"""
Metrics router — Overview KPIs, funnel, trend, and root cause breakdown.
"""
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models import Case, Diagnosis, Outcome
from app.models.case import CaseStatus
from app.schemas import MetricsOverview, FunnelStage, TrendPoint, RootCauseBreakdown

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    # Case counts by status
    status_counts = {}
    for s in CaseStatus:
        count = await db.scalar(
            select(func.count()).select_from(Case).where(Case.status == s, Case.organization_id == organization.id)
        )
        status_counts[s.value] = count or 0

    total_cases = sum(status_counts.values())

    # Total at risk
    total_at_risk = await db.scalar(
        select(func.sum(Case.amount_at_risk)).select_from(Case).where(Case.organization_id == organization.id)
    ) or 0

    # Total recovered
    total_recovered = await db.scalar(
        select(func.sum(Case.recovered_amount)).select_from(Case)
        .where(Case.status == CaseStatus.recovered, Case.organization_id == organization.id)
    ) or 0

    recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0

    # Avg time to recovery (hours)
    result = await db.execute(
        select(Case.opened_at, Case.closed_at)
        .where(and_(Case.status == CaseStatus.recovered, Case.closed_at.isnot(None), Case.organization_id == organization.id))
        .limit(200)
    )
    rows = result.all()
    if rows:
        hours_list = [(r.closed_at - r.opened_at).total_seconds() / 3600 for r in rows]
        avg_hours = sum(hours_list) / len(hours_list)
    else:
        avg_hours = 0.0

    return MetricsOverview(
        total_at_risk_paise=total_at_risk,
        total_recovered_paise=total_recovered,
        recovery_rate_pct=round(recovery_rate, 1),
        avg_time_to_recovery_hours=round(avg_hours, 1),
        cases_open=status_counts.get("open", 0),
        cases_in_progress=status_counts.get("in_progress", 0),
        cases_recovered=status_counts.get("recovered", 0),
        cases_escalated=status_counts.get("escalated", 0),
        cases_written_off=status_counts.get("written_off", 0),
        cases_human_pending=status_counts.get("human_pending", 0),
        total_cases=total_cases,
    )


@router.get("/funnel", response_model=List[FunnelStage])
async def get_funnel(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    total = await db.scalar(select(func.count()).select_from(Case).where(Case.organization_id == organization.id)) or 0
    total_risk = await db.scalar(select(func.sum(Case.amount_at_risk)).select_from(Case).where(Case.organization_id == organization.id)) or 0

    diagnosed = await db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.status != CaseStatus.open, Case.organization_id == organization.id)
    ) or 0

    intervened = await db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.status.in_([
            CaseStatus.in_progress, CaseStatus.recovered,
            CaseStatus.escalated, CaseStatus.written_off, CaseStatus.human_pending
        ]), Case.organization_id == organization.id)
    ) or 0

    recovered = await db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.status == CaseStatus.recovered, Case.organization_id == organization.id)
    ) or 0
    recovered_paise = await db.scalar(
        select(func.sum(Case.recovered_amount)).select_from(Case)
        .where(Case.status == CaseStatus.recovered, Case.organization_id == organization.id)
    ) or 0

    escalated = await db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.status.in_([CaseStatus.escalated, CaseStatus.human_pending]), Case.organization_id == organization.id)
    ) or 0

    written_off = await db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.status == CaseStatus.written_off, Case.organization_id == organization.id)
    ) or 0

    return [
        FunnelStage(stage="detected", label="Detected", count=total, paise=total_risk, color="#94A3B8"),
        FunnelStage(stage="diagnosed", label="Diagnosed", count=diagnosed, paise=int(total_risk * diagnosed / max(total, 1)), color="#3395FF"),
        FunnelStage(stage="intervened", label="Intervened", count=intervened, paise=int(total_risk * intervened / max(total, 1)), color="#F59E0B"),
        FunnelStage(stage="recovered", label="Recovered", count=recovered, paise=recovered_paise, color="#22C55E"),
        FunnelStage(stage="escalated", label="Escalated", count=escalated, paise=int(total_risk * escalated / max(total, 1)), color="#EF4444"),
        FunnelStage(stage="written_off", label="Written Off", count=written_off, paise=int(total_risk * written_off / max(total, 1)), color="#64748B"),
    ]


@router.get("/trend", response_model=List[TrendPoint])
async def get_trend(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Recovered ₹ per day over the last N days."""
    points = []
    for i in range(days - 1, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        recovered = await db.scalar(
            select(func.sum(Case.recovered_amount))
            .where(and_(
                Case.status == CaseStatus.recovered,
                Case.closed_at >= day_start,
                Case.closed_at < day_end,
                Case.organization_id == organization.id,
            ))
        ) or 0

        points.append(TrendPoint(date=day_start.strftime("%Y-%m-%d"), recovered_paise=recovered))

    return points


@router.get("/root-causes", response_model=List[RootCauseBreakdown])
async def get_root_causes(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Root cause breakdown with counts and amounts."""
    from app.seed.decline_codes import ROOT_CAUSE_LABELS

    result = await db.execute(
        select(Diagnosis.root_cause, func.count(Diagnosis.id).label("count"))
        .join(Case)
        .where(Case.organization_id == organization.id)
        .group_by(Diagnosis.root_cause)
        .order_by(func.count(Diagnosis.id).desc())
    )
    rows = result.all()

    breakdowns = []
    for row in rows:
        breakdowns.append(RootCauseBreakdown(
            root_cause=row.root_cause,
            label=ROOT_CAUSE_LABELS.get(row.root_cause, row.root_cause.replace("_", " ").title()),
            count=row.count,
            paise=0,  # simplified; join with cases for amount
        ))
    return breakdowns
