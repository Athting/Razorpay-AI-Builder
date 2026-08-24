"""
Diagnosis Worker — Celery task that classifies why a payment failed.

Flow: payment_event → root_cause_classifier → Diagnosis record → policy queue
"""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.config import settings


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@celery_app.task(name="app.workers.diagnosis_worker.run_diagnosis", bind=True, max_retries=3)
def run_diagnosis(self, case_id: str, payment_event_id: str):
    """
    Given a case_id and payment_event_id, classify the failure root cause,
    write a Diagnosis record, update the case status, and enqueue the policy worker.
    """
    import asyncio
    from app.models import Case, PaymentEvent, Diagnosis, CaseStatus
    from app.models.audit_log import AuditActor

    db = _get_sync_session()
    try:
        case_uuid = uuid.UUID(case_id)
        event_uuid = uuid.UUID(payment_event_id)

        # Load case and event
        case = db.get(Case, case_uuid)
        event = db.get(PaymentEvent, event_uuid)
        if not case or not event:
            return {"error": "Case or event not found"}

        customer = case.customer

        # Run async classifier in sync context
        from app.services.ai.root_cause_classifier import classify as async_classify
        loop = asyncio.new_event_loop()
        diagnosis_result = loop.run_until_complete(async_classify(
            decline_code=event.decline_code,
            gateway_message=event.gateway_message,
            customer_tenure_days=customer.tenure_days if customer else 0,
            customer_segment=customer.segment.value if customer else "consumer",
            past_attempts=case.attempt_count,
        ))
        loop.close()

        # Write Diagnosis
        diagnosis = Diagnosis(
            id=uuid.uuid4(),
            case_id=case_uuid,
            root_cause=diagnosis_result.root_cause,
            confidence=diagnosis_result.confidence,
            model_version=diagnosis_result.model_version,
            reasoning_text=diagnosis_result.reasoning_text,
            suggested_channel=diagnosis_result.suggested_channel,
            created_at=datetime.utcnow(),
        )
        db.add(diagnosis)

        # Update case status
        case.status = CaseStatus.in_progress
        db.commit()

        # Append to audit log (sync version)
        _sync_audit_append(
            db=db,
            case_id=case_uuid,
            actor="model",
            action=f"diagnosed:{diagnosis_result.root_cause}",
            reasoning=f"Root cause classified as '{diagnosis_result.root_cause}' "
                      f"(confidence: {diagnosis_result.confidence:.0%}, "
                      f"model: {diagnosis_result.model_version}). "
                      f"{diagnosis_result.reasoning_text}",
        )
        db.commit()

        # Chain to policy worker
        from app.workers.policy_worker import run_policy
        run_policy.apply_async(args=[case_id], queue="policy")

        return {
            "case_id": case_id,
            "root_cause": diagnosis_result.root_cause,
            "confidence": diagnosis_result.confidence,
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


def _sync_audit_append(db: Session, case_id: uuid.UUID, actor: str, action: str, reasoning: str):
    """Synchronous version of audit_service.append for use in Celery workers."""
    import hashlib
    from app.models.audit_log import AuditLog

    last = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    prev_hash = last.hash if last else "genesis_block_0000"
    timestamp_str = datetime.utcnow().isoformat()
    row_data = f"{prev_hash}|{case_id}|{actor}|{action}|{timestamp_str}|{reasoning}"
    new_hash = hashlib.sha256(row_data.encode()).hexdigest()

    entry = AuditLog(
        id=uuid.uuid4(),
        case_id=case_id,
        actor=actor,
        action=action,
        reasoning=reasoning,
        policy_version="v1.0",
        timestamp=datetime.utcnow(),
        prev_hash=prev_hash,
        hash=new_hash,
    )
    db.add(entry)
