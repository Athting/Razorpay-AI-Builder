"""
Promise Tracker — Extracts payment promise details from free-text customer replies.

Input:  Raw text (SMS/WhatsApp/email reply from customer)
Output: {promised_date, promised_amount_paise, confidence}
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.config import settings


@dataclass
class PromiseResult:
    promised_date: Optional[date]
    promised_amount_paise: Optional[int]
    confidence: float
    summary: str


# ── Regex patterns for date extraction ──
_DATE_PATTERNS = [
    (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', 'dmy'),
    (r'\b(today)\b', 'today'),
    (r'\b(tomorrow|kal|kal tak)\b', 'tomorrow'),
    (r'\bin (\d+) days?\b', 'in_days'),
    (r'\bby (\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', 'day_month'),
    (r'\bby (this|next) (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 'weekday'),
    (r'\b(\d{1,2}) (january|february|march|april|may|june|july|august|september|october|november|december)\b', 'day_month_full'),
]

_AMOUNT_PATTERNS = [
    r'(?:rs|₹|inr)\.?\s*(\d[\d,]*)',
    r'(\d[\d,]*)\s*(?:rs|₹|rupees|inr)',
    r'(\d[\d,]*)\s*(?:thousand|k)\b',
]

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
}

_WEEKDAY_MAP = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}


def _extract_date(text: str) -> Optional[date]:
    text_lower = text.lower()
    today = date.today()

    if re.search(r'\btoday\b', text_lower):
        return today
    if re.search(r'\b(tomorrow|kal|kal tak)\b', text_lower):
        return today + timedelta(days=1)

    m = re.search(r'\bin (\d+) days?\b', text_lower)
    if m:
        return today + timedelta(days=int(m.group(1)))

    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    m = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b', text_lower)
    if m:
        day = int(m.group(1))
        month = _MONTH_MAP.get(m.group(2)[:3], 0)
        if month:
            year = today.year if month >= today.month else today.year + 1
            try:
                return date(year, month, day)
            except ValueError:
                pass

    m = re.search(r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text_lower)
    if m:
        modifier, weekday_name = m.group(1), m.group(2)
        target_day = _WEEKDAY_MAP[weekday_name]
        days_ahead = (target_day - today.weekday()) % 7
        if modifier == 'next':
            days_ahead = days_ahead or 7
        return today + timedelta(days=days_ahead)

    return None


def _extract_amount_paise(text: str) -> Optional[int]:
    text_lower = text.lower()
    for pattern in _AMOUNT_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            raw = m.group(1).replace(',', '')
            if 'thousand' in text_lower or 'k' in m.group(0):
                return int(float(raw) * 1000 * 100)
            return int(float(raw) * 100)
    return None


def _is_positive_intent(text: str) -> bool:
    positive = ['will pay', 'will transfer', 'payment', 'paying', 'transfer',
                'aaj karunga', 'kal karunga', 'kal dunga', 'send', 'done by',
                'by tomorrow', 'by today', 'karta hu', 'kar dunga', 'karenge']
    text_lower = text.lower()
    return any(kw in text_lower for kw in positive)


async def extract_promise(text: str, case_amount_paise: int = 0) -> PromiseResult:
    """
    Extract a payment promise from customer free text.
    Returns: PromiseResult with date, amount, confidence, summary.
    """
    if settings.gemini_configured:
        try:
            import google.generativeai as genai
            import json, re
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                f"""Extract payment promise details from this customer message.
Message: "{text}"

Respond in JSON only (no markdown):
{{"promised_date": "YYYY-MM-DD or null", "promised_amount_inr": <int or null>, "confidence": <0-1>, "summary": "<one line>"}}"""
            )
            raw = response.text.strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('`').strip()
            data = json.loads(raw)
            promised_date = None
            if data.get('promised_date'):
                try:
                    promised_date = date.fromisoformat(data['promised_date'])
                except Exception:
                    pass
            inr = data.get('promised_amount_inr')
            paise = inr * 100 if inr else None
            return PromiseResult(
                promised_date=promised_date,
                promised_amount_paise=paise,
                confidence=float(data.get('confidence', 0.5)),
                summary=data.get('summary', 'Promise extracted via Gemini.'),
            )
        except Exception:
            pass

    return _mock_extract(text, case_amount_paise)


def _mock_extract(text: str, case_amount_paise: int) -> PromiseResult:
    """Rule-based extraction fallback."""
    promised_date = _extract_date(text)
    promised_amount_paise = _extract_amount_paise(text)
    positive = _is_positive_intent(text)

    confidence = 0.3
    if promised_date:
        confidence += 0.35
    if promised_amount_paise:
        confidence += 0.20
    if positive:
        confidence += 0.15

    summary = "No clear promise detected."
    if promised_date and positive:
        date_str = promised_date.strftime("%d %b %Y")
        amount_str = f"₹{(promised_amount_paise or case_amount_paise) // 100:,}" if (promised_amount_paise or case_amount_paise) else ""
        summary = f"Customer promised to pay {amount_str} by {date_str}."
    elif positive:
        summary = "Customer expressed intent to pay but no date specified."

    return PromiseResult(
        promised_date=promised_date,
        promised_amount_paise=promised_amount_paise or case_amount_paise,
        confidence=round(min(confidence, 0.95), 2),
        summary=summary,
    )
