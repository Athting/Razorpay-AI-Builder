"""
Synthetic data generator for the AI Revenue Recovery demo.
Generates 500 failed subscription charges + 100 overdue invoices
with realistic Indian customer profiles and varied decline codes.
"""
import random
import uuid
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import (
    Customer, PaymentEvent, Case, StoppingRule,
    CustomerSegment, CaseType, CaseStatus,
)
from app.seed.decline_codes import DECLINE_CODE_MAP, DECLINE_CODE_WEIGHTS

# ─── Indian locale data ───
INDIAN_FIRST_NAMES = [
    "Arjun", "Priya", "Rahul", "Ananya", "Vikram", "Sneha", "Amit", "Pooja",
    "Rohit", "Kavya", "Suresh", "Divya", "Kiran", "Meera", "Aditya", "Nisha",
    "Rajesh", "Sunita", "Deepak", "Lakshmi", "Sanjay", "Rekha", "Manoj", "Geeta",
    "Nikhil", "Swati", "Varun", "Preeti", "Ajay", "Shweta", "Gaurav", "Anjali",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Singh", "Gupta", "Verma", "Yadav", "Joshi",
    "Nair", "Reddy", "Iyer", "Mehta", "Shah", "Jain", "Agarwal", "Pandey",
    "Malhotra", "Kapoor", "Bose", "Das", "Mishra", "Tiwari", "Srivastava",
]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Surat", "Nagpur",
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"]

# Subscription plan amounts (paise)
SUBSCRIPTION_AMOUNTS = [
    9900, 19900, 29900, 49900, 99900, 149900, 199900, 299900, 499900,
]

# B2B invoice amounts (paise) — larger
INVOICE_AMOUNTS = [
    500000, 750000, 1000000, 1500000, 2000000, 3000000, 5000000,
    750000, 1250000, 2500000, 4000000, 10000000,
]


def _weighted_choice(weights_dict: dict) -> str:
    keys = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def _random_customer_name() -> tuple[str, str]:
    first = random.choice(INDIAN_FIRST_NAMES)
    last = random.choice(INDIAN_LAST_NAMES)
    return first, last


def _random_phone() -> str:
    prefixes = ["98", "99", "70", "80", "90", "91", "77", "88", "63", "62"]
    prefix = random.choice(prefixes)
    rest = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"+91{prefix}{rest}"


def _random_email(first: str, last: str) -> str:
    domain = random.choice(EMAIL_DOMAINS)
    suffix = random.randint(1, 999)
    return f"{first.lower()}.{last.lower()}{suffix}@{domain}"


def _random_date_in_past(days_back: int = 30) -> datetime:
    delta = timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))
    return datetime.utcnow() - delta


def _random_gateway_message(decline_code: str) -> str:
    entry = DECLINE_CODE_MAP.get(decline_code, DECLINE_CODE_MAP["UNKNOWN"])
    variants = [
        f"Payment declined: {entry['description']}",
        f"Transaction failed - {entry['label']}",
        f"Bank response: {decline_code} - {entry['description'][:60]}",
    ]
    return random.choice(variants)


def _channel_opts_for_segment(segment: CustomerSegment) -> dict:
    if segment == CustomerSegment.consumer:
        return {
            "whatsapp": random.random() > 0.15,
            "sms": random.random() > 0.05,
            "email": random.random() > 0.20,
            "voice": random.random() > 0.60,
        }
    elif segment == CustomerSegment.smb:
        return {
            "whatsapp": random.random() > 0.20,
            "sms": random.random() > 0.10,
            "email": True,
            "voice": random.random() > 0.40,
        }
    else:  # enterprise
        return {
            "whatsapp": False,
            "sms": False,
            "email": True,
            "voice": random.random() > 0.30,
        }


async def seed_all(db: AsyncSession) -> dict:
    """
    Main entry point. Check if already seeded, then create all synthetic data.
    Returns counts of created entities.
    """
    # Check if already seeded
    count = await db.scalar(select(func.count()).select_from(Customer))
    if count and count > 0:
        return {"message": "Already seeded", "customers": count}

    created = {
        "customers": 0, "payment_events": 0, "cases": 0, "stopping_rules": 0
    }

    # ─── 1. Create Customers ───
    customers: List[Customer] = []
    n_customers = 60  # diverse customer pool

    for i in range(n_customers):
        first, last = _random_customer_name()
        # Segment distribution: 60% consumer, 30% SMB, 10% enterprise
        r = random.random()
        if r < 0.60:
            segment = CustomerSegment.consumer
        elif r < 0.90:
            segment = CustomerSegment.smb
        else:
            segment = CustomerSegment.enterprise

        # Risk score: higher for those with past failures
        risk_score = round(random.betavariate(2, 3), 2)  # skewed toward medium-low

        customer = Customer(
            id=uuid.uuid4(),
            name=f"{first} {last}",
            phone=_random_phone(),
            email=_random_email(first, last),
            segment=segment,
            risk_score=risk_score,
            dnd_opt_out=random.random() < 0.08,  # 8% opted out
            channel_opts=_channel_opts_for_segment(segment),
            city=random.choice(INDIAN_CITIES),
            created_at=_random_date_in_past(days_back=730),  # up to 2 years old
        )
        db.add(customer)
        customers.append(customer)
        created["customers"] += 1

    await db.flush()

    # ─── 2. Create Subscription Failure Events + Cases (500) ───
    for i in range(500):
        customer = random.choice(customers)
        decline_code = _weighted_choice(DECLINE_CODE_WEIGHTS)
        amount = random.choice(SUBSCRIPTION_AMOUNTS)
        event_time = _random_date_in_past(days_back=30)

        event = PaymentEvent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            source="razorpay",
            event_type="subscription.charged.failure",
            amount=amount,
            currency="INR",
            decline_code=decline_code,
            gateway_message=_random_gateway_message(decline_code),
            raw_payload_json={
                "entity": "event",
                "account_id": "acc_mock123",
                "event": "subscription.charged",
                "payload": {
                    "subscription": {"entity": {"id": f"sub_{uuid.uuid4().hex[:8]}"}},
                    "payment": {
                        "entity": {
                            "id": f"pay_{uuid.uuid4().hex[:8]}",
                            "amount": amount,
                            "currency": "INR",
                            "error_code": decline_code,
                            "error_description": _random_gateway_message(decline_code),
                        }
                    },
                },
            },
            created_at=event_time,
        )
        db.add(event)

        # Create corresponding case
        case = Case(
            id=uuid.uuid4(),
            customer_id=customer.id,
            payment_event_id=event.id,
            type=CaseType.subscription_failure,
            status=CaseStatus.open,
            amount_at_risk=amount,
            opened_at=event_time,
            recovered_amount=0,
        )
        db.add(case)
        created["payment_events"] += 1
        created["cases"] += 1

    # ─── 3. Create Invoice Overdue Events + Cases (100) ───
    for i in range(100):
        customer = random.choice([c for c in customers if c.segment != CustomerSegment.consumer])
        if not customer:
            customer = random.choice(customers)

        amount = random.choice(INVOICE_AMOUNTS)
        # Invoices are older — 7 to 90 days
        days_overdue = random.randint(7, 90)
        event_time = datetime.utcnow() - timedelta(days=days_overdue)

        event = PaymentEvent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            source="razorpay",
            event_type="invoice.expired",
            amount=amount,
            currency="INR",
            decline_code=None,
            gateway_message=f"Invoice overdue by {days_overdue} days",
            raw_payload_json={
                "entity": "event",
                "event": "invoice.expired",
                "payload": {
                    "invoice": {
                        "entity": {
                            "id": f"inv_{uuid.uuid4().hex[:8]}",
                            "amount": amount,
                            "currency": "INR",
                            "description": f"B2B Invoice - {customer.name}",
                        }
                    }
                },
            },
            created_at=event_time,
        )
        db.add(event)

        case = Case(
            id=uuid.uuid4(),
            customer_id=customer.id,
            payment_event_id=event.id,
            type=CaseType.invoice_overdue,
            status=CaseStatus.open,
            amount_at_risk=amount,
            opened_at=event_time,
            recovered_amount=0,
        )
        db.add(case)
        created["payment_events"] += 1
        created["cases"] += 1

    # ─── 4. Create Default Stopping Rules ───
    default_rules = [
        StoppingRule(
            id=uuid.uuid4(),
            name="Global Max Attempts",
            max_attempts=3,
            cooldown_hours=24,
            quiet_hours_start=21,
            quiet_hours_end=9,
            applies_to="all",
            active=True,
        ),
        StoppingRule(
            id=uuid.uuid4(),
            name="Subscription Recovery",
            max_attempts=4,
            cooldown_hours=48,
            quiet_hours_start=22,
            quiet_hours_end=8,
            applies_to="subscription_failure",
            active=True,
        ),
        StoppingRule(
            id=uuid.uuid4(),
            name="Invoice Chaser",
            max_attempts=5,
            cooldown_hours=72,
            quiet_hours_start=20,
            quiet_hours_end=9,
            applies_to="invoice_overdue",
            active=True,
        ),
        StoppingRule(
            id=uuid.uuid4(),
            name="30-Day Hard Stop",
            max_attempts=10,
            cooldown_hours=24,
            quiet_hours_start=21,
            quiet_hours_end=9,
            applies_to="all",
            active=True,
        ),
    ]
    for rule in default_rules:
        db.add(rule)
        created["stopping_rules"] += 1

    await db.commit()
    return created
