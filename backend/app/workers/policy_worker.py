"""
Policy Worker — Scores available actions, applies stopping rules, creates Intervention records.
"""
import uuid
import hashlib
from datetime import datetime, timedelta

from app.workers.celery_app import celery_app
from app.core.config import settings


def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _sync_audit(db, case_id, actor, action, reasoning):
    import hashlib
    from app.models.audit_log import AuditLog
    last = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    prev_hash = last.hash if last else "genesis_block_0000"
    ts = datetime.utcnow().isoformat()
    row_data = f"{prev_hash}|{case_id}|{actor}|{action}|{ts}|{reasoning}"
    new_hash = hashlib.sha256(row_data.encode()).hexdigest()
    entry = AuditLog(
        id=uuid.uuid4(), case_id=case_id, actor=actor, action=action,
        reasoning=reasoning, policy_version="v1.0",
        timestamp=datetime.utcnow(), prev_hash=prev_hash, hash=new_hash,
    )
    db.add(entry)


@celery_app.task(name="app.workers.policy_worker.run_policy", bind=True, max_retries=3)
def run_policy(self, case_id: str):
    """
    Score recovery actions for a case, apply stopping rules, create Intervention.
    """
    from app.models import Case, Diagnosis, Intervention, StoppingRule
    from app.models.intervention import ActionType, Channel, InterventionResult
    from app.models.audit_log import AuditLog
    from app.services.ai.policy_engine import score_actions, is_within_quiet_hours
    from sqlalchemy import and_

    db = _get_sync_session()
    try:
        case_uuid = uuid.UUID(case_id)
        case = db.get(Case, case_uuid)
        if not case:
            return {"error": "Case not found"}

        customer = case.customer
        if not customer:
            return {"error": "Customer not found"}

        # Get latest diagnosis
        latest_diagnosis = (
            db.query(Diagnosis)
            .filter(Diagnosis.case_id == case_uuid)
            .order_by(Diagnosis.created_at.desc())
            .first()
        )
        root_cause = latest_diagnosis.root_cause if latest_diagnosis else "unknown"

        # Get applicable stopping rules
        rules = (
            db.query(StoppingRule)
            .filter(
                StoppingRule.active == True,
                StoppingRule.applies_to.in_([case.type.value, "all"]),
            )
            .all()
        )

        # Determine effective limits
        max_attempts = min((r.max_attempts for r in rules), default=3)
        cooldown_hours = max((r.cooldown_hours for r in rules), default=24)
        quiet_start = min((r.quiet_hours_start for r in rules), default=21)
        quiet_end = max((r.quiet_hours_end for r in rules), default=9)

        # Count existing interventions
        existing_interventions = (
            db.query(Intervention)
            .filter(Intervention.case_id == case_uuid)
            .all()
        )
        attempt_count = len(existing_interventions)

        # Hours since case opened
        hours_since = (datetime.utcnow() - case.opened_at).total_seconds() / 3600

        # Check cooldown — don't act if last intervention was too recent
        if existing_interventions:
            last_attempt = max(
                (i.executed_at or i.scheduled_at for i in existing_interventions),
                default=case.opened_at,
            )
            hours_since_last = (datetime.utcnow() - last_attempt).total_seconds() / 3600
            if hours_since_last < cooldown_hours:
                return {
                    "case_id": case_id,
                    "status": "cooldown",
                    "retry_in_hours": cooldown_hours - hours_since_last,
                }

        within_quiet = is_within_quiet_hours(quiet_start, quiet_end)

        # Score actions
        scored = score_actions(
            root_cause=root_cause,
            amount_paise=case.amount_at_risk,
            customer_segment=customer.segment.value,
            customer_tenure_days=customer.tenure_days,
            dnd_opt_out=customer.dnd_opt_out,
            channel_opts=customer.channel_opts or {},
            past_recovery_rate=0.35,  # synthetic default; replace with real metric
            hours_since_failure=hours_since,
            attempt_count=attempt_count,
            max_attempts=max_attempts,
            is_within_quiet_hours=within_quiet,
            case_days_open=case.days_open,
        )

        if not scored:
            return {"case_id": case_id, "status": "no_actions"}

        top_action = scored[0]

        # Determine scheduled_at (respect cooldown)
        if within_quiet:
            # Schedule for next morning
            now = datetime.utcnow()
            scheduled_at = now.replace(hour=quiet_end, minute=0, second=0) + timedelta(days=1)
        else:
            scheduled_at = datetime.utcnow() + timedelta(minutes=5)

        # Build all action scores as JSON for the UI
        action_scores_payload = [
            {
                "action_type": a.action_type,
                "channel": a.channel,
                "expected_recovery_prob": a.expected_recovery_prob,
                "reasoning": a.reasoning,
                "requires_human_approval": a.requires_human_approval,
            }
            for a in scored
        ]

        # Create intervention
        intervention = Intervention(
            id=uuid.uuid4(),
            case_id=case_uuid,
            action_type=top_action.action_type,
            channel=top_action.channel,
            payload={"action_scores": action_scores_payload},
            scheduled_at=scheduled_at,
            result=InterventionResult.pending,
            attempt_number=attempt_count + 1,
            approved_by_human=top_action.requires_human_approval is False,
            expected_recovery_prob=top_action.expected_recovery_prob,
            reasoning=top_action.reasoning,
        )

        # If requires human approval, update case status
        if top_action.requires_human_approval:
            from app.models.case import CaseStatus
            case.status = CaseStatus.human_pending

        db.add(intervention)

        _sync_audit(
            db, case_uuid, "model",
            f"intervention_planned:{top_action.action_type}",
            f"Policy engine selected '{top_action.action_type}' via {top_action.channel}. "
            f"Expected recovery probability: {top_action.expected_recovery_prob:.0%}. "
            f"Reasoning: {top_action.reasoning}",
        )
        db.commit()

        # Queue execution
        if not top_action.requires_human_approval:
            from app.workers.execution_worker import execute_intervention
            execute_intervention.apply_async(
                args=[str(intervention.id)],
                eta=scheduled_at,
                queue="execution",
            )

        return {
            "case_id": case_id,
            "action": top_action.action_type,
            "channel": top_action.channel,
            "scheduled_at": scheduled_at.isoformat(),
        }

    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
