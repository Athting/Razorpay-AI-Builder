"""
Message generator — produces channel-specific recovery messages.
Uses Google Gemini Pro when configured, with rich mock messages as fallback.
Supports WhatsApp, SMS, Email, and Voice (Hinglish TTS scripts).
"""
import re
from dataclasses import dataclass
from typing import Dict, Optional

from app.core.config import settings


@dataclass
class MessageResult:
    channel: str
    message: str
    email_subject: Optional[str]
    tts_script: Optional[str]
    payment_link: Optional[str]


# ── Mock message templates by channel and root cause ──
_MOCK_MESSAGES: Dict[str, Dict[str, str]] = {
    "whatsapp": {
        "insufficient_funds": "Hi {name}! 🙏 Aapka ₹{amount} ka payment process nahi ho saka. Account mein funds add karke retry karein — link: {link}",
        "card_expired": "Hi {name}! Aapka card expire ho gaya hai. Card update karein aur payment complete karein: {link}",
        "mandate_expired": "Hi {name}! Aapka auto-debit mandate expire ho gaya hai. Please re-register: {link}",
        "upi_failure": "Hi {name}! UPI payment fail hua. Doosra payment method try karein: {link}",
        "generic_decline": "Hi {name}! Aapka ₹{amount} payment pending hai. 1 tap mein complete karein: {link}",
    },
    "sms": {
        "insufficient_funds": "URGENT: ₹{amount} payment failed. Low balance. Pay now: {link}",
        "card_expired": "Card expired. Update & pay ₹{amount}: {link}",
        "generic_decline": "Payment of ₹{amount} failed. Retry: {link}",
    },
    "email": {
        "card_expired": "Your card ending in the registered number has expired. Please update your payment method to continue your subscription.",
        "fraud_suspected": "For security, your payment was paused. Please verify your identity and complete the payment.",
        "generic_decline": "Your recent payment of ₹{amount} was unsuccessful. Please click below to update your payment details.",
    },
    "voice": {
        "generic_decline": "Namaste! Main {company} se bol raha hoon. Aapka payment pending hai. Kya aap abhi complete karna chahenge?",
        "issuer_intervention": "Hello! We noticed your payment needs phone verification with your bank. Shall we help you complete this?",
    },
}

_EMAIL_SUBJECTS = {
    "card_expired": "Action Required: Update your payment method",
    "fraud_suspected": "Security Alert: Payment verification needed",
    "mandate_expired": "Re-authorize your auto-debit mandate",
    "generic_decline": "Your payment needs attention",
    "insufficient_funds": "Complete your pending payment",
}


async def generate(
    customer_name: str,
    channel: str,
    root_cause: str,
    amount_paise: int,
    payment_link: str,
    customer_segment: str = "consumer",
    company_name: str = "RevRecov",
) -> MessageResult:
    """Generate a personalized recovery message for the given channel."""
    amount_inr = f"₹{amount_paise // 100:,}"

    if settings.gemini_configured:
        return await _generate_with_gemini(
            customer_name, channel, root_cause, amount_inr, payment_link,
            customer_segment, company_name,
        )

    return _generate_mock(
        customer_name, channel, root_cause, amount_inr, payment_link, company_name,
    )


async def _generate_with_gemini(
    name: str, channel: str, root_cause: str, amount: str,
    link: str, segment: str, company: str,
) -> MessageResult:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)

    channel_instructions = {
        "whatsapp": "Write a WhatsApp message in Hinglish (mix of Hindi and English). Friendly, ≤160 chars. Use 1-2 emojis. Include payment link.",
        "sms": "Write an SMS in English. Very concise, ≤120 chars. Include payment link.",
        "email": "Write the email body (plain text, 3-4 sentences) and suggest a subject line. Professional, empathetic.",
        "voice": "Write a Hindi/Hinglish IVR script (≤40 words). Natural spoken language, not formal. Also write an English fallback (≤40 words).",
    }
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = f"""You are a recovery message writer for an Indian payment platform.
Generate a personalized payment recovery message.

Customer: {name}
Channel: {channel}
Root Cause: {root_cause.replace('_', ' ')}
Amount: {amount}
Customer Segment: {segment}
Payment Link: {link}
Company: {company}

Instructions: {channel_instructions.get(channel, 'Write a professional message.')}

Respond in JSON only (no markdown):
{{
  "message": "<main message text>",
  "email_subject": "<subject line or null>",
  "tts_script": "<Hinglish TTS script if voice channel, else null>"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
        import json
        data = json.loads(text)
        return MessageResult(
            channel=channel,
            message=data.get("message", ""),
            email_subject=data.get("email_subject"),
            tts_script=data.get("tts_script"),
            payment_link=link,
        )
    except Exception:
        return _generate_mock(name, channel, root_cause, amount, link, company)


def _generate_mock(
    name: str, channel: str, root_cause: str,
    amount: str, link: str, company: str,
) -> MessageResult:
    """Rich, deterministic mock messages — no API call needed."""
    channel_templates = _MOCK_MESSAGES.get(channel, _MOCK_MESSAGES["whatsapp"])
    template = channel_templates.get(root_cause, channel_templates.get("generic_decline", "Payment of {amount} is pending: {link}"))

    message = template.format(
        name=name.split()[0],  # first name only
        amount=amount,
        link=link,
        company=company,
    )

    subject = _EMAIL_SUBJECTS.get(root_cause, "Action Required: Complete your payment") if channel == "email" else None

    tts = None
    if channel == "voice":
        tts = f"Namaste {name.split()[0]} ji! Main {company} se bol raha hoon. Aapka {amount} ka payment pending hai. Kya aap abhi {link} par jaake complete kar sakte hain? Dhanyawad!"

    return MessageResult(
        channel=channel,
        message=message,
        email_subject=subject,
        tts_script=tts,
        payment_link=link,
    )
