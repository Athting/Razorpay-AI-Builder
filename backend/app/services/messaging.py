"""Provider adapters for real recovery communications.

Credentials are workspace scoped; mock delivery is used only when MOCK_MODE is true.
"""
import httpx
from app.core.config import settings


def send(channel: str, config: dict, recipient: str | None, message: str, subject: str | None = None) -> dict:
    if settings.MOCK_MODE:
        return {"status": "delivered", "provider": "mock"}
    if not recipient:
        return {"status": "failed", "reason": "No recipient address for selected channel"}

    try:
        if channel == "email":
            api_key, sender = config.get("resend_api_key"), config.get("sender_email")
            if not api_key or not sender:
                return {"status": "failed", "reason": "Email provider is not configured"}
            response = httpx.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {api_key}"}, json={
                "from": sender, "to": [recipient], "subject": subject or "Payment reminder", "text": message,
            }, timeout=15)
        elif channel in {"sms", "whatsapp"}:
            sid, token = config.get("twilio_account_sid"), config.get("twilio_auth_token")
            sender = config.get("twilio_whatsapp_from") if channel == "whatsapp" else config.get("twilio_from_number")
            if not sid or not token or not sender:
                return {"status": "failed", "reason": f"Twilio {channel} is not configured"}
            destination = f"whatsapp:{recipient}" if channel == "whatsapp" and not recipient.startswith("whatsapp:") else recipient
            response = httpx.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", auth=(sid, token), data={"From": sender, "To": destination, "Body": message}, timeout=15)
        else:
            return {"status": "failed", "reason": f"Unsupported delivery channel: {channel}"}
        if response.is_error:
            return {"status": "failed", "reason": f"Provider response {response.status_code}"}
        body = response.json()
        return {"status": "delivered", "provider_id": body.get("id") or body.get("sid")}
    except httpx.HTTPError:
        return {"status": "failed", "reason": "Provider could not be reached"}
