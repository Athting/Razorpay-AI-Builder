"""
Case Manager — Deduplication and state-machine transitions for recovery cases.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.case import Case, CaseType, CaseStatus
from app.models.payment_event import PaymentEvent
from app.models.audit_log import AuditActor



def _event_type_to_case_type(event_type: str) -> CaseType:
    if "subscription" in event_type.lower():
        return CaseType.subscription_failure
    elif "invoice" in event_type.lower():
        return CaseType.invoice_overdue
    elif "order" in event_type.lower() or "checkout" in event_type.lower():
        return CaseType.checkout_abandoned
    return CaseType.subscription_failure


async def get_or_create_case(
    db: AsyncSession,
    payment_event: PaymentEvent,
) -> Case:
    """
    Deduplicate: find an existing open/in_progress case for this customer + type.
    If found, return it. Otherwise create a new case.
    """
    case_type = _event_type_to_case_type(payment_event.event_type)

    # Look for an open case for this customer + type
    stmt = select(Case).where(
        and_(
            Case.customer_id == payment_event.customer_id,
            Case.type == case_type,
            Case.status.in_([CaseStatus.open, CaseStatus.in_progress]),
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Create new case
    new_case = Case(
        id=uuid.uuid4(),
        organization_id=payment_event.organization_id,
        customer_id=payment_event.customer_id,
        payment_event_id=payment_event.id,
        type=case_type,
        status=CaseStatus.open,
        amount_at_risk=payment_event.amount,
        opened_at=datetime.utcnow(),
        recovered_amount=0,
    )
    db.add(new_case)
    await db.flush()

    # Audit log
    from app.services.audit_service import append as audit_append
    await audit_append(
        db=db,
        actor=AuditActor.system,
        action="case_opened",
        reasoning=f"New {case_type.value} case opened for customer {payment_event.customer_id}. "
                  f"Payment event: {payment_event.event_type}, amount: ₹{payment_event.amount // 100:,}.",
        case_id=new_case.id,
    )

    return new_case


async def transition_status(
    db: AsyncSession,
    case: Case,
    new_status: CaseStatus,
    actor: AuditActor = AuditActor.system,
    reasoning: str = "",
    recovered_amount: Optional[int] = None,
) -> Case:
    """
    Transition a case to a new status and log the transition in audit.
    """
    old_status = case.status
    case.status = new_status

    if new_status in (CaseStatus.recovered, CaseStatus.written_off, CaseStatus.escalated):
        case.closed_at = datetime.utcnow()

    if recovered_amount is not None:
        case.recovered_amount = recovered_amount

    await db.flush()

    from app.services.audit_service import append as audit_append
    await audit_append(
        db=db,
        actor=actor,
        action=f"status_changed:{old_status.value}->{new_status.value}",
        reasoning=reasoning or f"Case status changed from {old_status.value} to {new_status.value}.",
        case_id=case.id,
    )

    return case
