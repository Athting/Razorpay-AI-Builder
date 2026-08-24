import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid
import enum

from app.core.database import Base


class AuditActor(str, enum.Enum):
    system = "system"
    model = "model"
    human = "human"


class AuditLog(Base):
    """
    Append-only, hash-chained audit log.
    Each row stores:
      - prev_hash: hash of the previous row (or "genesis_block_0000" for the first)
      - hash: SHA-256(prev_hash + case_id + actor + action + timestamp + reasoning)
    This chain makes tampering detectable.
    """
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.id"), nullable=True)
    actor: Mapped[AuditActor] = mapped_column(SAEnum(AuditActor), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    reasoning: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    policy_version: Mapped[str] = mapped_column(String(20), default="v1.0", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    case = relationship("Case", back_populates="audit_logs")
