"""
Policy Engine — Scored decision table for recovery action selection.

Given: root_cause, amount, customer profile, attempt count, stopping rules
Returns: ranked list of allowed actions with expected recovery probability + reasoning.

This is intentionally explainable (not a black box) — every action score has a reason string.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import random


@dataclass
class ScoredAction:
    action_type: str
    channel: str
    expected_recovery_prob: float
    reasoning: str
    requires_human_approval: bool = False


# ─── Base scores by action ───
_BASE_SCORES = {
    "send_reminder":       0.75,
    "generate_payment_link": 0.72,
    "retry_payment":       0.65,
    "send_offer":          0.55,
    "escalate_to_human":   0.30,
    "write_off":           0.05,
}

# Root causes where retry is pointless
_NO_RETRY_CAUSES = {
    "invalid_card", "expired_card", "lost_card", "stolen_card",
    "mandate_revoked", "suspected_fraud", "transaction_not_permitted",
    "restricted_card", "blocked_first_use", "pin_attempts_exceeded",
}

# Root causes where payment link is the best move
_LINK_PREFERRED_CAUSES = {
    "expired_card", "invalid_card", "mandate_revoked", "blocked_first_use",
}

# Best channel per root cause
_PREFERRED_CHANNELS = {
    "insufficient_funds": "whatsapp",
    "expired_card": "email",
    "invalid_card": "email",
    "do_not_honor": "email",
    "issuer_unavailable": "sms",
    "mandate_revoked": "voice",
    "system_error": "sms",
    "technical_error": "sms",
    "unknown": "whatsapp",
    "no_funds": "whatsapp",
    "exceeds_limit": "whatsapp",
}

# High-value threshold: require human approval for offers
_OFFER_HUMAN_APPROVAL_PAISE = 500_000  # ₹5,000
_ESCALATE_AUTO_PAISE = 1_000_000        # ₹10,000


def score_actions(
    root_cause: str,
    amount_paise: int,
    customer_segment: str,
    customer_tenure_days: int,
    dnd_opt_out: bool,
    channel_opts: dict,
    past_recovery_rate: float,
    hours_since_failure: float,
    attempt_count: int,
    max_attempts: int,
    is_within_quiet_hours: bool,
    case_days_open: int,
    can_retry: bool = True,
) -> List[ScoredAction]:
    """
    Score all valid actions and return them ranked by expected_recovery_prob.
    Respects stopping rules, DND, channel opts, and compliance constraints.
    """
    actions: List[ScoredAction] = []

    # ── Hard stops ──
    if dnd_opt_out:
        # DND: only system actions allowed, no customer contact
        actions.append(ScoredAction(
            action_type="escalate_to_human",
            channel="system",
            expected_recovery_prob=0.20,
            reasoning="Customer is on DND. Escalating to human agent for manual outreach via approved channel.",
        ))
        return actions

    if attempt_count >= max_attempts:
        # Max attempts reached
        if amount_paise >= _ESCALATE_AUTO_PAISE:
            actions.append(ScoredAction(
                action_type="escalate_to_human",
                channel="system",
                expected_recovery_prob=0.25,
                reasoning=f"Maximum automated attempts ({max_attempts}) reached. High-value case (₹{amount_paise//100:,}) escalated to human agent.",
                requires_human_approval=False,
            ))
        else:
            actions.append(ScoredAction(
                action_type="write_off",
                channel="system",
                expected_recovery_prob=0.00,
                reasoning=f"Maximum attempts ({max_attempts}) exhausted and amount (₹{amount_paise//100:,}) below escalation threshold. Writing off.",
            ))
        return actions

    if case_days_open >= 30 and amount_paise < 10_000:
        actions.append(ScoredAction(
            action_type="write_off",
            channel="system",
            expected_recovery_prob=0.00,
            reasoning=f"Case is {case_days_open} days old with low amount (₹{amount_paise//100:,}). Auto write-off triggered.",
        ))
        return actions

    if is_within_quiet_hours:
        # Return deferred reminder (will be scheduled post quiet hours)
        preferred_ch = _preferred_channel(root_cause, channel_opts)
        actions.append(ScoredAction(
            action_type="send_reminder",
            channel=preferred_ch,
            expected_recovery_prob=0.45,
            reasoning="Currently within quiet hours (9pm–9am). Reminder scheduled for next active window.",
        ))
        return actions

    preferred_ch = _preferred_channel(root_cause, channel_opts)

    # ── Score each action ──

    # 1. Retry payment
    if can_retry and root_cause not in _NO_RETRY_CAUSES:
        score = _BASE_SCORES["retry_payment"]
        score += 0.10 if root_cause in {"issuer_unavailable", "system_error", "technical_error"} else 0
        score += 0.05 if hours_since_failure >= 24 else -0.10  # retry after waiting
        score += 0.05 if customer_tenure_days > 180 else 0
        score = min(score, 0.95)
        actions.append(ScoredAction(
            action_type="retry_payment",
            channel="system",
            expected_recovery_prob=round(score, 3),
            reasoning=(
                f"Root cause '{root_cause}' is retry-eligible. "
                f"{'Waiting {:.0f}h improves success probability. '.format(hours_since_failure) if hours_since_failure >= 4 else ''}"
                f"Customer tenure ({customer_tenure_days} days) and past recovery rate ({past_recovery_rate:.0%}) factored in."
            ),
        ))

    # 2. Send reminder (most broadly applicable)
    if channel_opts.get(preferred_ch, True):
        score = _BASE_SCORES["send_reminder"]
        score += 0.10 if root_cause in {"insufficient_funds", "no_funds"} else 0
        score -= 0.10 if attempt_count > 1 else 0
        score += 0.05 if past_recovery_rate > 0.3 else 0
        score = min(score, 0.92)
        actions.append(ScoredAction(
            action_type="send_reminder",
            channel=preferred_ch,
            expected_recovery_prob=round(score, 3),
            reasoning=(
                f"Sending {preferred_ch} reminder with payment link. "
                f"Channel chosen based on root cause '{root_cause}' and customer opt-in. "
                f"Attempt #{attempt_count + 1} of {max_attempts}."
            ),
        ))

    # 3. Generate payment link (especially for card-update scenarios)
    if root_cause in _LINK_PREFERRED_CAUSES or attempt_count == 0:
        score = _BASE_SCORES["generate_payment_link"]
        score += 0.15 if root_cause in _LINK_PREFERRED_CAUSES else 0
        score += 0.05 if customer_segment in {"smb", "enterprise"} else 0
        score = min(score, 0.92)
        actions.append(ScoredAction(
            action_type="generate_payment_link",
            channel=preferred_ch,
            expected_recovery_prob=round(score, 3),
            reasoning=(
                f"Fresh payment link sent via {preferred_ch}. "
                f"{'Card-update scenario — direct link avoids saved-card failure. ' if root_cause in _LINK_PREFERRED_CAUSES else ''}"
                f"Customer can pay immediately without re-entering subscription flow."
            ),
        ))

    # 4. Send offer (discount) — for high-value or stuck cases
    if amount_paise >= 50_000 and attempt_count >= 1:  # ₹500+, at least 1 attempt
        discount_pct = 10 if amount_paise < 500_000 else 5
        score = _BASE_SCORES["send_offer"]
        score += 0.15 if customer_tenure_days > 365 else 0  # loyal customers
        score += 0.10 if attempt_count >= 2 else 0
        score = min(score, 0.80)
        requires_approval = amount_paise >= _OFFER_HUMAN_APPROVAL_PAISE
        actions.append(ScoredAction(
            action_type="send_offer",
            channel="email" if customer_segment == "enterprise" else preferred_ch,
            expected_recovery_prob=round(score, 3),
            reasoning=(
                f"Offering {discount_pct}% discount to recover ₹{amount_paise//100:,}. "
                f"{'Requires human approval due to high value. ' if requires_approval else ''}"
                f"Customer tenure of {customer_tenure_days} days suggests retention value."
            ),
            requires_human_approval=requires_approval,
        ))

    # 5. Auto-escalate for high-value
    if amount_paise >= _ESCALATE_AUTO_PAISE or attempt_count >= max_attempts - 1:
        score = _BASE_SCORES["escalate_to_human"]
        score += 0.15 if amount_paise >= _ESCALATE_AUTO_PAISE else 0
        actions.append(ScoredAction(
            action_type="escalate_to_human",
            channel="system",
            expected_recovery_prob=round(score, 3),
            reasoning=(
                f"{'High-value case (₹' + str(amount_paise // 100) + ',000+) flagged for human review. ' if amount_paise >= _ESCALATE_AUTO_PAISE else ''}"
                f"{'Approaching attempt limit. ' if attempt_count >= max_attempts - 1 else ''}"
                f"Human agent has full case context for personalized outreach."
            ),
        ))

    # Sort by expected_recovery_prob descending
    actions.sort(key=lambda x: x.expected_recovery_prob, reverse=True)
    return actions


def _preferred_channel(root_cause: str, channel_opts: dict) -> str:
    preferred = _PREFERRED_CHANNELS.get(root_cause, "email")
    if channel_opts.get(preferred, False):
        return preferred
    # Fallback order
    for ch in ["whatsapp", "sms", "email", "voice"]:
        if channel_opts.get(ch, False):
            return ch
    return "email"


def is_within_quiet_hours(quiet_start: int, quiet_end: int) -> bool:
    """Check if current UTC hour falls within quiet hours."""
    now_hour = datetime.now(timezone.utc).hour
    if quiet_start > quiet_end:  # spans midnight (e.g., 21–9)
        return now_hour >= quiet_start or now_hour < quiet_end
    return quiet_start <= now_hour < quiet_end
