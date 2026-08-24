from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.models.customer import CustomerSegment
from app.models.case import CaseType, CaseStatus
from app.models.diagnosis import Diagnosis
from app.models.intervention import ActionType, Channel, InterventionResult
from app.models.outcome import OutcomeType


# ─── Customer ───
class CustomerBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    segment: CustomerSegment = CustomerSegment.consumer
    risk_score: float = 0.5
    dnd_opt_out: bool = False
    channel_opts: Dict[str, bool] = {"whatsapp": True, "sms": True, "email": True, "voice": False}
    city: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: uuid.UUID
    created_at: datetime
    tenure_days: int

    class Config:
        from_attributes = True


# ─── Diagnosis ───
class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    case_id: uuid.UUID
    root_cause: str
    confidence: float
    model_version: str
    reasoning_text: str
    suggested_channel: str
    created_at: datetime

# ─── Intervention ───
class InterventionResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    action_type: ActionType
    channel: Channel
    payload: Dict[str, Any]
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    result: InterventionResult
    attempt_number: int
    approved_by_human: bool
    expected_recovery_prob: Optional[float] = None
    reasoning: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Outcome ───
class OutcomeResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    intervention_id: Optional[uuid.UUID] = None
    outcome: OutcomeType
    amount: int
    promised_date: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True


# ─── Case ───
class CaseListItem(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer: Optional[CustomerResponse] = None
    type: CaseType
    status: CaseStatus
    amount_at_risk: int
    recovered_amount: int
    opened_at: datetime
    closed_at: Optional[datetime] = None
    days_open: int
    attempt_count: int
    latest_root_cause: Optional[str] = None
    latest_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class CaseDetail(CaseListItem):
    diagnoses: List[DiagnosisResponse] = []
    interventions: List[InterventionResponse] = []
    outcomes: List[OutcomeResponse] = []

    class Config:
        from_attributes = True


class CaseFilters(BaseModel):
    type: Optional[str] = None
    status: Optional[str] = None
    root_cause: Optional[str] = None
    min_amount: Optional[int] = None
    max_amount: Optional[int] = None
    search: Optional[str] = None
    page: int = 1
    size: int = 20


class PaginatedCases(BaseModel):
    items: List[CaseListItem]
    total: int
    page: int
    size: int
    pages: int


# ─── Audit ───
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    case_id: Optional[uuid.UUID] = None
    actor: str
    action: str
    reasoning: str
    policy_version: str
    timestamp: datetime
    prev_hash: str
    hash: str

    class Config:
        from_attributes = True


class AuditVerifyResponse(BaseModel):
    valid: bool
    total_entries: int
    broken_at: Optional[uuid.UUID] = None
    message: str


# ─── Stopping Rules ───
class StoppingRuleBase(BaseModel):
    name: str
    max_attempts: int = 3
    cooldown_hours: int = 24
    quiet_hours_start: int = 21
    quiet_hours_end: int = 9
    applies_to: str = "all"
    active: bool = True


class StoppingRuleCreate(StoppingRuleBase):
    pass


class StoppingRuleUpdate(StoppingRuleBase):
    pass


class StoppingRuleResponse(StoppingRuleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Metrics ───
class MetricsOverview(BaseModel):
    total_at_risk_paise: int
    total_recovered_paise: int
    recovery_rate_pct: float
    avg_time_to_recovery_hours: float
    cases_open: int
    cases_in_progress: int
    cases_recovered: int
    cases_escalated: int
    cases_written_off: int
    cases_human_pending: int
    total_cases: int


class FunnelStage(BaseModel):
    stage: str
    label: str
    count: int
    paise: int
    color: str


class TrendPoint(BaseModel):
    date: str
    recovered_paise: int


class RootCauseBreakdown(BaseModel):
    root_cause: str
    label: str
    count: int
    paise: int
