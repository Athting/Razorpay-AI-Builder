"""
Outcome Listener — Records payment success outcomes and closes the recovery loop.
"""
import uuid
import hashlib
import random
from datetime import datetime

from app.workers.celery_app import celery_app
from app.core.config import settings


def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _sync_audit(db, case_id, actor, action, reasoning):
    from app.models.audit_log import AuditLog
    last = db.query(AuditLog).filter(AuditLog.case_id == case_id).order_by(AuditLog.timestamp.desc()).first()
    prev_hash = last.hash if last else "genesis_block_0000"
    ts = datetime.utcnow().isoformat()
    new_hash = hashlib.sha256(f"{prev_hash}|{case_id}|{actor}|{action}|{ts}|{reasoning}".encode()).hexdigest()
    db.add(AuditLog(
        id=uuid.uuid4(), case_id=case_id, actor=actor, action=action,
        reasoning=reasoning, policy_version="v1.0",
        timestamp=datetime.utcnow(), prev_hash=prev_hash, hash=new_hash,
    ))


@celery_app.task(name="app.workers.outcome_listener.record_payment_outcome", bind=True, max_retries=3)
def record_payment_outcome(self, case_id: str, intervention_id: str = None):
    """
    Record a successful payment outcome (triggered by payment.captured webhook or simulated).
    Closes the loop: updates case to 'recovered', records Outcome.
    """
    from app.models import Case, Outcome
    from app.models.outcome import OutcomeType
    from app.models.case import CaseStatus
    from app.models.intervention import Intervention, InterventionResult

    db = _get_sync_session()
    try:
        case_uuid = uuid.UUID(case_id)
        case = db.get(Case, case_uuid)
        if not case or case.status == CaseStatus.recovered:
            return {"status": "already_recovered_or_not_found"}

        # Record outcome
        outcome = Outcome(
            id=uuid.uuid4(),
            case_id=case_uuid,
            intervention_id=uuid.UUID(intervention_id) if intervention_id else None,
            outcome=OutcomeType.paid,
            amount=case.amount_at_risk,
            recorded_at=datetime.utcnow(),
        )
        db.add(outcome)

        # Close the case
        case.status = CaseStatus.recovered
        case.recovered_amount = case.amount_at_risk
        case.closed_at = datetime.utcnow()

        # Update intervention result if present
        if intervention_id:
            iv = db.get(Intervention, uuid.UUID(intervention_id))
            if iv:
                iv.result = InterventionResult.responded

        _sync_audit(db, case_uuid, "system", "payment_captured",
                   f"Payment of ₹{case.amount_at_risk // 100:,} received. "
                   f"Case {case_uuid} marked as recovered. "
                   f"Recovery loop closed successfully.")
        db.commit()

        return {"case_id": case_id, "status": "recovered", "amount": case.amount_at_risk}

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
