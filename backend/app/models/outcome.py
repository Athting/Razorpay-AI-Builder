import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class OutcomeType(str, enum.Enum):
    paid = "paid"
    promised = "promised"
    ignored = "ignored"
    disputed = "disputed"
    opted_out = "opted_out"


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id"), nullable=False)
    intervention_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("interventions.id"), nullable=True)
    outcome: Mapped[OutcomeType] = mapped_column(SAEnum(OutcomeType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # paise
    promised_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="outcomes")
    intervention = relationship("Intervention", back_populates="outcomes")
