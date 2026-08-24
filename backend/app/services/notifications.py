"""Operational notifications for workspace escalation events."""
import httpx
from app.core.config import settings


def notify_escalation(config: dict, case_id: str, amount_paise: int) -> None:
    if settings.MOCK_MODE or not config.get("escalation_alerts", True):
        return
    webhook = config.get("slack_webhook_url")
    if not webhook:
        return
    try:
        httpx.post(webhook, json={"text": f"Recovery case {case_id} needs human review (₹{amount_paise / 100:,.2f})."}, timeout=10)
    except httpx.HTTPError:
        # Notification delivery is non-blocking: it must never fail a recovery workflow.
        pass
