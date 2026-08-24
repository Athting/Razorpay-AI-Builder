"""
Audit Service — Append-only, SHA-256 hash-chained audit log writer.

Every AI decision, system action, and human override is recorded here.
The hash chain makes tampering detectable: each row's hash covers itself + the previous row's hash.
"""
import hashlib
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit_log import AuditLog, AuditActor


def _compute_hash(prev_hash: str, case_id: Optional[str], actor: str, action: str,
                  timestamp: str, reasoning: str) -> str:
    """SHA-256 hash of the concatenated row fields + previous hash."""
    row_data = f"{prev_hash}|{case_id}|{actor}|{action}|{timestamp}|{reasoning}"
    return hashlib.sha256(row_data.encode("utf-8")).hexdigest()


async def append(
    db: AsyncSession,
    actor: AuditActor,
    action: str,
    reasoning: str,
    case_id: Optional[uuid.UUID] = None,
    policy_version: str = "v1.0",
) -> AuditLog:
    """
    Append a new entry to the hash-chained audit log.
    Automatically computes prev_hash from the last entry for this case.
    """
    # Get the last audit entry for this case (or globally if no case_id)
    if case_id:
        stmt = (
            select(AuditLog)
            .where(AuditLog.case_id == case_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(1)
        )
    else:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1)

    result = await db.execute(stmt)
    last_entry = result.scalar_one_or_none()

    prev_hash = last_entry.hash if last_entry else "genesis_block_0000"
    timestamp_str = datetime.utcnow().isoformat()

    new_hash = _compute_hash(
        prev_hash=prev_hash,
        case_id=str(case_id) if case_id else "global",
        actor=actor.value if hasattr(actor, "value") else str(actor),
        action=action,
        timestamp=timestamp_str,
        reasoning=reasoning,
    )

    entry = AuditLog(
        id=uuid.uuid4(),
        case_id=case_id,
        actor=actor,
        action=action,
        reasoning=reasoning,
        policy_version=policy_version,
        timestamp=datetime.utcnow(),
        prev_hash=prev_hash,
        hash=new_hash,
    )
    db.add(entry)
    await db.flush()  # get the ID assigned without full commit
    return entry


async def verify_chain(db: AsyncSession, case_id: uuid.UUID) -> dict:
    """
    Re-compute the entire hash chain for a case and verify integrity.
    Returns: {valid: bool, total_entries: int, broken_at: Optional[UUID]}
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.case_id == case_id)
        .order_by(AuditLog.timestamp.asc())
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return {"valid": True, "total_entries": 0, "broken_at": None}

    prev_hash = "genesis_block_0000"
    for entry in entries:
        expected_hash = _compute_hash(
            prev_hash=prev_hash,
            case_id=str(case_id),
            actor=entry.actor.value if hasattr(entry.actor, "value") else str(entry.actor),
            action=entry.action,
            timestamp=entry.timestamp.isoformat(),
            reasoning=entry.reasoning,
        )
        if expected_hash != entry.hash:
            return {
                "valid": False,
                "total_entries": len(entries),
                "broken_at": str(entry.id),
                "message": f"Hash mismatch at entry {entry.id}. Chain integrity violated.",
            }
        prev_hash = entry.hash

    return {
        "valid": True,
        "total_entries": len(entries),
        "broken_at": None,
        "message": f"✓ Chain verified — {len(entries)} entries, all hashes valid.",
    }
