"""
Execution Worker — Fires scheduled interventions (retry payments, send messages, generate links).
"""
import uuid
import hashlib
import random
from datetime import datetime

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.secrets import unseal


def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _sync_audit(db, case_id, actor, action, reasoning):
    import hashlib
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


def _mock_retry_payment(amount_paise: int) -> dict:
    """Simulate a payment retry with realistic success/failure rates."""
    success_rate = 0.40  # 40% base retry success
    if random.random() < success_rate:
        return {"status": "success", "payment_id": f"pay_{uuid.uuid4().hex[:8]}", "amount": amount_paise}
    decline_codes = ["51", "91", "05", "96", "UNKNOWN"]
    weights = [40, 20, 15, 15, 10]
    code = random.choices(decline_codes, weights=weights)[0]
    return {"status": "failed", "decline_code": code, "message": f"Retry failed with code {code}"}


def _mock_generate_payment_link(amount_paise: int, customer_name: str) -> str:
    link_id = uuid.uuid4().hex[:8]
    return f"https://rzp.io/l/mock-{link_id}"


def _mock_send_message(channel: str, payload: dict) -> dict:
    """Simulate message delivery with realistic success rates."""
    delivery_rates = {"whatsapp": 0.92, "sms": 0.88, "email": 0.95, "voice": 0.65}
    rate = delivery_rates.get(channel, 0.85)
    if random.random() < rate:
        return {"status": "delivered", "message_id": f"msg_{uuid.uuid4().hex[:8]}"}
    return {"status": "failed", "reason": "Delivery failure"}


@celery_app.task(name="app.workers.execution_worker.execute_intervention", bind=True, max_retries=3)
def execute_intervention(self, intervention_id: str):
    """
    Execute a scheduled intervention:
    - retry_payment: call Razorpay retry API (or mock)
    - send_reminder / send_offer / generate_payment_link: generate message, send via channel
    - escalate_to_human: update case to human_pending
    - write_off: close case
    """
    import asyncio
    from app.models import Case, Intervention, Outcome
    from app.models.intervention import InterventionResult, ActionType
    from app.models.outcome import OutcomeType
    from app.models.case import CaseStatus

    db = _get_sync_session()
    try:
        iv_uuid = uuid.UUID(intervention_id)
        intervention = db.get(Intervention, iv_uuid)
        if not intervention:
            return {"error": "Intervention not found"}

        if intervention.executed_at:
            return {"status": "already_executed"}

        case = db.get(Case, intervention.case_id)
        customer = case.customer
        from app.models.organization import Organization
        organization = db.get(Organization, case.organization_id) if case.organization_id else None
        action = intervention.action_type

        result_status = InterventionResult.failed
        payload_update = dict(intervention.payload or {})

        # ── Generate payment link for messaging actions ──
        payment_link = _mock_generate_payment_link(case.amount_at_risk, customer.name)

        # ── Execute based on action type ──
        if action == ActionType.retry_payment:
            result = _mock_retry_payment(case.amount_at_risk)
            if result["status"] == "success":
                result_status = InterventionResult.responded
                # Create outcome
                outcome = Outcome(
                    id=uuid.uuid4(),
                    case_id=case.id,
                    intervention_id=intervention.id,
                    outcome=OutcomeType.paid,
                    amount=case.amount_at_risk,
                    recorded_at=datetime.utcnow(),
                )
                db.add(outcome)
                case.status = CaseStatus.recovered
                case.recovered_amount = case.amount_at_risk
                case.closed_at = datetime.utcnow()
                payload_update["retry_result"] = result
                _sync_audit(db, case.id, "system", "payment_recovered",
                           f"Payment retry successful! ₹{case.amount_at_risk // 100:,} recovered via Razorpay retry API.")
            else:
                result_status = InterventionResult.failed
                payload_update["retry_result"] = result
                _sync_audit(db, case.id, "system", "retry_failed",
                           f"Payment retry failed with code {result.get('decline_code', 'unknown')}. Will schedule next intervention.")

        elif action in (ActionType.send_reminder, ActionType.send_offer):
            loop = asyncio.new_event_loop()
            from app.services.ai.message_generator import generate_message
            msg_result = loop.run_until_complete(generate_message(
                customer_name=customer.name,
                amount_paise=case.amount_at_risk,
                action_type=action.value,
                channel=intervention.channel.value,
                customer_segment=customer.segment.value,
                payment_link=payment_link,
            ))
            loop.close()

            payload_update["message"] = msg_result.text
            payload_update["payment_link"] = payment_link
            if msg_result.subject:
                payload_update["email_subject"] = msg_result.subject
            if msg_result.tts_script:
                payload_update["tts_script"] = msg_result.tts_script

            recipient = customer.email if intervention.channel.value == "email" else customer.phone
            from app.services.messaging import send
            send_result = send(intervention.channel.value, unseal(organization.communication_config) if organization else {}, recipient, msg_result.text, msg_result.subject)
            result_status = (
                InterventionResult.delivered
                if send_result["status"] == "delivered"
                else InterventionResult.failed
            )
            payload_update["send_result"] = send_result
            _sync_audit(db, case.id, "model", f"message_sent:{intervention.channel.value}",
                       f"Recovery message sent via {intervention.channel.value}. "
                       f"Action: {action.value}. Delivery status: {send_result['status']}. "
                       f"Message preview: {msg_result.text[:100]}...")

        elif action == ActionType.generate_payment_link:
            loop = asyncio.new_event_loop()
            from app.services.ai.message_generator import generate_message
            msg_result = loop.run_until_complete(generate_message(
                customer_name=customer.name,
                amount_paise=case.amount_at_risk,
                action_type="generate_payment_link",
                channel=intervention.channel.value,
                payment_link=payment_link,
            ))
            loop.close()

            payload_update["message"] = msg_result.text
            payload_update["payment_link"] = payment_link

            recipient = customer.email if intervention.channel.value == "email" else customer.phone
            from app.services.messaging import send
            send_result = send(intervention.channel.value, unseal(organization.communication_config) if organization else {}, recipient, msg_result.text)
            result_status = (
                InterventionResult.delivered
                if send_result["status"] == "delivered"
                else InterventionResult.failed
            )
            _sync_audit(db, case.id, "system", "payment_link_generated",
                       f"Fresh payment link generated and sent via {intervention.channel.value}. Link: {payment_link}")

        elif action == ActionType.escalate_to_human:
            case.status = CaseStatus.human_pending
            result_status = InterventionResult.sent
            if organization:
                from app.services.notifications import notify_escalation
                notify_escalation(organization.notification_config or {}, str(case.id), case.amount_at_risk)
            _sync_audit(db, case.id, "system", "escalated_to_human",
                       f"Case escalated to human agent. Amount: ₹{case.amount_at_risk // 100:,}. "
                       f"Full context and case history available in escalation queue.")

        elif action == ActionType.write_off:
            case.status = CaseStatus.written_off
            case.closed_at = datetime.utcnow()
            result_status = InterventionResult.sent
            _sync_audit(db, case.id, "system", "written_off",
                       f"Case written off. Amount ₹{case.amount_at_risk // 100:,} below recovery threshold "
                       f"after {intervention.attempt_number} attempts over {case.days_open} days.")

        # Update intervention
        intervention.executed_at = datetime.utcnow()
        intervention.result = result_status
        intervention.payload = payload_update

        db.commit()

        # Delivery failures are transient often enough to deserve bounded,
        # auditable retries. Do not retry policy/escalation actions.
        if result_status == InterventionResult.failed and action in (ActionType.send_reminder, ActionType.send_offer, ActionType.generate_payment_link):
            retry_count = int(payload_update.get("delivery_retry_count", 0))
            if retry_count < 3:
                payload_update["delivery_retry_count"] = retry_count + 1
                intervention.payload = payload_update
                intervention.executed_at = None
                intervention.result = InterventionResult.pending
                db.commit()
                raise self.retry(countdown=60 * (2 ** retry_count))

        # If message delivered, schedule outcome check (simulate customer response)
        if result_status == InterventionResult.delivered and random.random() < 0.35:
            # 35% chance customer pays after reminder — simulate with outcome listener
            from app.workers.outcome_listener import record_payment_outcome
            record_payment_outcome.apply_async(
                args=[str(case.id), str(intervention.id)],
                countdown=random.randint(300, 3600),  # 5min–1h delay
                queue="outcomes",
            )

        return {"intervention_id": intervention_id, "result": result_status.value}

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
