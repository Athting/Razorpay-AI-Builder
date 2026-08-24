"""
Audit router — Hash-chained audit log viewer and integrity verifier.
"""
import csv
import io
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.tenancy import get_current_organization
from app.models.case import Case
from app.models.organization import Organization
from app.models.audit_log import AuditLog
from app.schemas import AuditLogResponse, AuditVerifyResponse
from app.services.audit_service import append, verify_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{case_id}", response_model=List[AuditLogResponse])
async def get_audit_trail(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Get the full hash-chained audit log for a case."""
    result = await db.execute(
        select(AuditLog).join(Case).where(AuditLog.case_id == case_id, Case.organization_id == organization.id)
        .order_by(AuditLog.timestamp.asc())
    )
    entries = result.scalars().all()
    return [AuditLogResponse.model_validate(e) for e in entries]


@router.get("/{case_id}/verify", response_model=AuditVerifyResponse)
async def verify_audit_chain(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Re-compute the hash chain and verify integrity."""
    owned_case = await db.scalar(select(Case.id).where(Case.id == case_id, Case.organization_id == organization.id))
    if not owned_case:
        raise HTTPException(status_code=404, detail="Case not found")
    verification = await verify_chain(db, case_id)
    return AuditVerifyResponse(
        valid=verification["valid"],
        total_entries=verification["total_entries"],
        broken_at=verification.get("broken_at"),
        message=verification.get("message", ""),
    )


@router.get("/{case_id}/export")
async def export_audit_csv(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
):
    """Export audit trail as CSV."""
    result = await db.execute(
        select(AuditLog).join(Case).where(AuditLog.case_id == case_id, Case.organization_id == organization.id)
        .order_by(AuditLog.timestamp.asc())
    )
    entries = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Actor", "Action", "Reasoning", "Policy Version", "Hash", "Prev Hash"])
    for e in entries:
        writer.writerow([
            e.timestamp.isoformat(),
            e.actor.value,
            e.action,
            e.reasoning,
            e.policy_version,
            e.hash,
            e.prev_hash,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_{case_id}.csv"},
    )
