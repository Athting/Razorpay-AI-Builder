"""
Webhooks router — Ingests Razorpay webhook events and seeds the recovery pipeline.
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models import PaymentEvent, Customer
from app.models.organization import Organization
from app.models.case import CaseStatus
from app.core.secrets import unseal
from app.models.customer import CustomerSegment
from app.services import case_manager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_razorpay_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/razorpay/{webhook_token}")
async def razorpay_webhook(
    webhook_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    organization = await db.scalar(
        select(Organization).where(
            Organization.webhook_token == webhook_token,
            Organization.is_active.is_(True),
        )
    )
    if not organization:
        raise HTTPException(status_code=404, detail="Unknown webhook workspace")

    credentials = unseal(organization.razorpay_oauth_config)
    webhook_secret = credentials.get("webhook_secret") or organization.razorpay_webhook_secret
    # A secret is mandatory for each connected production workspace.
    if not settings.MOCK_MODE:
        if not webhook_secret:
            raise HTTPException(status_code=503, detail="Webhook secret is not configured")
        if not _verify_razorpay_signature(body, signature, webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event", "")
    provider_event_id = request.headers.get("X-Razorpay-Event-Id") or payload.get("event_id")
    if provider_event_id:
        duplicate = await db.scalar(select(PaymentEvent).where(PaymentEvent.organization_id == organization.id, PaymentEvent.provider_event_id == provider_event_id))
        if duplicate:
            return {"status": "duplicate", "event_id": provider_event_id}

    # Payment success closes a matching open recovery case.
    success_events = {"payment.captured", "payment.authorized"}
    # Only process recovery-relevant events.
    failure_events = {
        "payment.failed", "subscription.charged.failure",
        "invoice.expired", "order.payment.failed",
    }
    if event_type not in failure_events | success_events:
        return {"status": "ignored", "event": event_type}

    # Extract amount and customer info
    payment_entity = (
        payload.get("payload", {}).get("payment", {}).get("entity", {})
        or payload.get("payload", {}).get("invoice", {}).get("entity", {})
        or {}
    )
    provider_payment_id = payment_entity.get("id")
    if event_type in success_events:
        from app.models import Case
        case = await db.scalar(select(Case).join(PaymentEvent).where(
            Case.organization_id == organization.id,
            PaymentEvent.provider_payment_id == provider_payment_id,
            Case.status.in_([CaseStatus.open, CaseStatus.in_progress, CaseStatus.human_pending]),
        ).order_by(Case.opened_at.desc()))
        if case:
            case.status = CaseStatus.recovered
            case.recovered_amount = case.amount_at_risk
            case.closed_at = datetime.utcnow()
            return {"status": "recovered", "case_id": str(case.id)}
        return {"status": "ignored", "event": event_type}
    amount = payment_entity.get("amount", 0)
    decline_code = payment_entity.get("error_code", "UNKNOWN")
    gateway_message = payment_entity.get("error_description", "")
    customer_email = payment_entity.get("email", "")
    customer_phone = payment_entity.get("contact", "")

    # Get or create customer
    from sqlalchemy import select
    result = await db.execute(
        select(Customer).where(
            Customer.organization_id == organization.id,
            Customer.email == customer_email,
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            id=uuid.uuid4(),
            organization_id=organization.id,
            name=customer_email.split("@")[0] if customer_email else "Unknown",
            email=customer_email or None,
            phone=customer_phone or None,
            segment=CustomerSegment.consumer,
            risk_score=0.5,
            channel_opts={"whatsapp": True, "sms": True, "email": True, "voice": False},
            created_at=datetime.utcnow(),
        )
        db.add(customer)
        await db.flush()

    # Create PaymentEvent
    event = PaymentEvent(
        id=uuid.uuid4(),
        organization_id=organization.id,
        customer_id=customer.id,
        source="razorpay",
        provider_event_id=provider_event_id,
        provider_payment_id=provider_payment_id,
        event_type=event_type,
        amount=amount,
        currency="INR",
        decline_code=decline_code,
        gateway_message=gateway_message,
        raw_payload_json=payload,
        created_at=datetime.utcnow(),
    )
    db.add(event)
    await db.flush()

    # Create or find case
    case = await case_manager.get_or_create_case(db, event)
    await db.commit()

    # Enqueue diagnosis
    from app.workers.diagnosis_worker import run_diagnosis
    run_diagnosis.apply_async(
        args=[str(case.id), str(event.id)],
        queue="diagnosis",
    )

    return {"status": "accepted", "case_id": str(case.id), "organization_id": str(organization.id)}


@router.post("/twilio/status/{webhook_token}")
async def twilio_delivery_status(webhook_token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Accept Twilio delivery callbacks and update the matching intervention."""
    organization = await db.scalar(select(Organization).where(Organization.webhook_token == webhook_token, Organization.is_active.is_(True)))
    if not organization:
        raise HTTPException(status_code=404, detail="Unknown webhook workspace")
    form = await request.form()
    provider_id, status_value = form.get("MessageSid"), str(form.get("MessageStatus", ""))
    if not provider_id:
        raise HTTPException(status_code=400, detail="Missing Twilio MessageSid")
    from app.models.intervention import Intervention, InterventionResult
    from app.models.case import Case
    rows = await db.execute(select(Intervention).join(Case).where(Case.organization_id == organization.id))
    for intervention in rows.scalars():
        if (intervention.payload or {}).get("send_result", {}).get("provider_id") == provider_id:
            intervention.result = InterventionResult.delivered if status_value in {"delivered", "sent", "read"} else InterventionResult.failed
            return {"status": "updated"}
    return {"status": "ignored"}
