import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, JSON, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class ActionType(str, enum.Enum):
    retry_payment = "retry_payment"
    send_reminder = "send_reminder"
    send_offer = "send_offer"
    escalate_to_human = "escalate_to_human"
    write_off = "write_off"
    generate_payment_link = "generate_payment_link"


class Channel(str, enum.Enum):
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"
    voice = "voice"
    system = "system"


class InterventionResult(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    responded = "responded"


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(SAEnum(ActionType), nullable=False)
    channel: Mapped[Channel] = mapped_column(SAEnum(Channel), default=Channel.system, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[InterventionResult] = mapped_column(
        SAEnum(InterventionResult), default=InterventionResult.pending, nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    approved_by_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expected_recovery_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Relationships
    case = relationship("Case", back_populates="interventions")
    outcomes = relationship("Outcome", back_populates="intervention", lazy="select")
