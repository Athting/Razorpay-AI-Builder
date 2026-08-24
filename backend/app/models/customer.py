import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, JSON, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class CustomerSegment(str, enum.Enum):
    consumer = "consumer"
    smb = "smb"
    enterprise = "enterprise"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("organizations.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    segment: Mapped[CustomerSegment] = mapped_column(
        SAEnum(CustomerSegment), default=CustomerSegment.consumer, nullable=False
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    dnd_opt_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    channel_opts: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"whatsapp": True, "sms": True, "email": True, "voice": False},
        nullable=False,
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    payment_events = relationship("PaymentEvent", back_populates="customer", lazy="select")
    cases = relationship("Case", back_populates="customer", lazy="select")

    @property
    def tenure_days(self) -> int:
        return (datetime.utcnow() - self.created_at).days
