import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class CaseType(str, enum.Enum):
    subscription_failure = "subscription_failure"
    invoice_overdue = "invoice_overdue"
    checkout_abandoned = "checkout_abandoned"


class CaseStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    recovered = "recovered"
    escalated = "escalated"
    written_off = "written_off"
    human_pending = "human_pending"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("customers.id"), nullable=False)
    payment_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("payment_events.id"), nullable=True)
    type: Mapped[CaseType] = mapped_column(SAEnum(CaseType), nullable=False)
    status: Mapped[CaseStatus] = mapped_column(SAEnum(CaseStatus), default=CaseStatus.open, nullable=False)
    amount_at_risk: Mapped[int] = mapped_column(Integer, nullable=False)  # paise
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recovered_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # paise

    # Relationships
    customer = relationship("Customer", back_populates="cases")
    payment_event = relationship("PaymentEvent", back_populates="cases")
    diagnoses = relationship("Diagnosis", back_populates="case", lazy="select", order_by="Diagnosis.created_at")
    interventions = relationship("Intervention", back_populates="case", lazy="select", order_by="Intervention.scheduled_at")
    outcomes = relationship("Outcome", back_populates="case", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="case", lazy="select", order_by="AuditLog.timestamp")

    @property
    def days_open(self) -> int:
        end = self.closed_at or datetime.utcnow()
        return (end - self.opened_at).days

    @property
    def attempt_count(self) -> int:
        return len(self.interventions) if self.interventions else 0
