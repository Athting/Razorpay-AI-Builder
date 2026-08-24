"""
Replay router — Triggers the batch replay pipeline on all open cases.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.organization import Organization
from app.models import Case, PaymentEvent
from app.models.case import CaseStatus

router = APIRouter(prefix="/replay", tags=["replay"])

_replay_jobs: dict = {}  # In-memory job tracker for demo


@router.post("/start")
async def start_replay(
    speed_multiplier: int = 1,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """
    Trigger batch replay of all open/unprocessed cases.
    Enqueues diagnosis → policy → execution pipeline for each case.
    """
    result = await db.execute(
        select(Case)
        .where(Case.status.in_([CaseStatus.open]), Case.organization_id == organization.id)
        .limit(600)
    )
    cases = result.scalars().all()

    job_id = str(uuid.uuid4())
    _replay_jobs[job_id] = {
        "status": "running",
        "total": len(cases),
        "processed": 0,
        "speed_multiplier": speed_multiplier,
    }

    # Enqueue diagnosis tasks for all open cases
    for case in cases:
        if case.payment_event_id:
            from app.workers.diagnosis_worker import run_diagnosis
            # Speed multiplier: divide countdown by multiplier
            delay = max(1, int(30 / speed_multiplier))
            run_diagnosis.apply_async(
                args=[str(case.id), str(case.payment_event_id)],
                countdown=delay,
                queue="diagnosis",
            )

    _replay_jobs[job_id]["processed"] = len(cases)
    _replay_jobs[job_id]["status"] = "queued"

    return {
        "job_id": job_id,
        "total_cases": len(cases),
        "message": f"Queued {len(cases)} cases for batch replay at {speed_multiplier}x speed",
    }


@router.get("/status/{job_id}")
async def replay_status(job_id: str, current_user=Depends(get_current_user), organization: Organization = Depends(get_current_organization)):
    job = _replay_jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job
