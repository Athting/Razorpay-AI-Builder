import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class RuleAppliesTo(str, enum.Enum):
    subscription_failure = "subscription_failure"
    invoice_overdue = "invoice_overdue"
    checkout_abandoned = "checkout_abandoned"
    all = "all"


class StoppingRule(Base):
    __tablename__ = "stopping_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=21, nullable=False)  # 9pm
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=9, nullable=False)    # 9am
    applies_to: Mapped[RuleAppliesTo] = mapped_column(
        SAEnum(RuleAppliesTo), default=RuleAppliesTo.all, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
