"""
Root-cause classifier — 2-tier system.
Tier 1: Rule-based lookup by decline code (fast, no API call needed).
Tier 2: Google Gemini Flash for edge cases without a known decline code.
"""
import re
from typing import Optional
from dataclasses import dataclass

from app.core.config import settings
from app.seed.decline_codes import DECLINE_CODE_MAP, ROOT_CAUSE_LABELS


@dataclass
class DiagnosisResult:
    root_cause: str
    confidence: float
    reasoning: str
    suggested_channel: str
    model_version: str


# Decline code → root cause mapping (from seed/decline_codes.py)
# High-confidence rule-based mappings
_RULE_BASED_CAUSES = {
    "insufficient_funds": ("insufficient_funds", 0.97, "Decline code maps directly to insufficient funds."),
    "do_not_honor":       ("do_not_honor_bank",  0.91, "Bank refused transaction — often temporary soft block."),
    "card_expired":       ("card_expired",        0.99, "Card expiry date has passed."),
    "invalid_card":       ("card_invalid",        0.95, "Card number / CVV failed Luhn check or is incorrect."),
    "lost_card":          ("card_lost_stolen",    0.99, "Card reported lost — requires customer action."),
    "stolen_card":        ("card_lost_stolen",    0.99, "Card reported stolen — requires customer action."),
    "pickup_card":        ("card_lost_stolen",    0.97, "Bank instructed card pickup — flagged for fraud."),
    "restricted_card":    ("card_restricted",     0.93, "Card has restrictions preventing this transaction type."),
    "card_velocity_exceeded": ("card_velocity",   0.92, "Too many transactions in a short window."),
    "transaction_not_permitted": ("card_restricted", 0.88, "Transaction type not permitted for this card."),
    "generic_decline":    ("generic_decline",     0.70, "Soft decline — reason unspecified by issuer."),
    "processor_declined": ("processor_error",     0.75, "Payment processor returned a soft decline."),
    "call_issuer":        ("issuer_intervention", 0.85, "Issuer requires phone verification from cardholder."),
    "fraudulent":         ("fraud_suspected",     0.96, "Issuer flagged this transaction as potentially fraudulent."),
    "authentication_required": ("3ds_required",  0.94, "3DS authentication needed but not completed."),
    "currency_not_supported": ("currency_issue",  0.93, "Card doesn't support INR or this currency."),
    "mandate_expired":    ("mandate_expired",     0.97, "e-Mandate registration has expired — re-registration needed."),
    "debit_blocked":      ("upi_failure",         0.89, "UPI or debit blocked by bank."),
    "upi_error":          ("upi_failure",         0.88, "UPI payment failed at gateway or PSP level."),
}

_CHANNEL_FOR_CAUSE = {
    "insufficient_funds": "whatsapp",
    "do_not_honor_bank":  "sms",
    "card_expired":       "email",
    "card_invalid":       "email",
    "card_lost_stolen":   "email",
    "card_restricted":    "email",
    "card_velocity":      "sms",
    "generic_decline":    "whatsapp",
    "processor_error":    "sms",
    "issuer_intervention": "voice",
    "fraud_suspected":    "email",
    "3ds_required":       "whatsapp",
    "currency_issue":     "email",
    "mandate_expired":    "whatsapp",
    "upi_failure":        "whatsapp",
}


async def classify(
    decline_code: Optional[str],
    gateway_message: Optional[str] = None,
    customer_segment: str = "consumer",
) -> DiagnosisResult:
    """
    Classify the root cause of a payment failure.
    Returns a DiagnosisResult with root_cause, confidence, reasoning, channel.
    """
    # ── Tier 1: Rule-based ──
    if decline_code and decline_code in _RULE_BASED_CAUSES:
        cause, confidence, reasoning = _RULE_BASED_CAUSES[decline_code]
        channel = _CHANNEL_FOR_CAUSE.get(cause, "email")
        return DiagnosisResult(
            root_cause=cause,
            confidence=confidence,
            reasoning=reasoning,
            suggested_channel=channel,
            model_version="rule-based-v1",
        )

    # ── Tier 2: Gemini Flash for ambiguous declines ──
    if settings.gemini_configured:
        return await _classify_with_gemini(decline_code, gateway_message, customer_segment)

    # ── Fallback: mock ──
    return _mock_classify(decline_code, gateway_message)


async def _classify_with_gemini(
    decline_code: Optional[str],
    gateway_message: Optional[str],
    customer_segment: str,
) -> DiagnosisResult:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are an expert payment failure analyst for an Indian fintech.
Analyze this payment failure and classify the root cause.

Decline code: {decline_code or 'unknown'}
Gateway message: {gateway_message or 'none'}
Customer segment: {customer_segment}

Available root causes (pick exactly one):
{', '.join(ROOT_CAUSE_LABELS.keys())}

Respond in this exact JSON format (no markdown):
{{"root_cause": "<one of the above>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>", "suggested_channel": "<whatsapp|sms|email|voice>"}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Remove markdown code fences if present
        text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
        import json
        data = json.loads(text)
        return DiagnosisResult(
            root_cause=data.get("root_cause", "generic_decline"),
            confidence=float(data.get("confidence", 0.65)),
            reasoning=data.get("reasoning", "Classified by Gemini."),
            suggested_channel=data.get("suggested_channel", "email"),
            model_version="gemini-2.5-flash",
        )
    except Exception as e:
        return _mock_classify(decline_code, gateway_message)


def _mock_classify(
    decline_code: Optional[str],
    gateway_message: Optional[str],
) -> DiagnosisResult:
    """Deterministic mock — no API call."""
    msg = (gateway_message or "").lower()
    if "fund" in msg or "balance" in msg:
        cause, conf = "insufficient_funds", 0.85
    elif "expired" in msg or "expiry" in msg:
        cause, conf = "card_expired", 0.90
    elif "upi" in msg:
        cause, conf = "upi_failure", 0.82
    elif "mandate" in msg:
        cause, conf = "mandate_expired", 0.88
    elif "fraud" in msg:
        cause, conf = "fraud_suspected", 0.78
    else:
        cause, conf = "generic_decline", 0.65

    return DiagnosisResult(
        root_cause=cause,
        confidence=conf,
        reasoning=f"Mock classifier: decline_code={decline_code}, msg snippet='{(gateway_message or '')[:60]}'.",
        suggested_channel=_CHANNEL_FOR_CAUSE.get(cause, "email"),
        model_version="mock-v1",
    )
