"""Organization scoping helpers for multi-tenant API requests."""
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.models.organization import Organization, OrganizationMember
from app.models.user import UserRole


async def get_current_organization(
    x_organization_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Organization:
    """Resolve the selected workspace and prove the user belongs to it."""
    stmt = select(Organization).join(OrganizationMember).where(
        OrganizationMember.user_id == current_user.id,
        Organization.is_active.is_(True),
    )
    if x_organization_id:
        stmt = stmt.where(Organization.id == x_organization_id)
    result = await db.execute(stmt.order_by(Organization.created_at))
    organization = result.scalars().first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active organization membership. Create a workspace first.",
        )
    return organization


async def ensure_personal_organization(db: AsyncSession, user, name: str | None = None) -> Organization:
    """Give a newly authenticated user a private workspace exactly once."""
    existing = await db.scalar(
        select(Organization).join(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    if existing:
        return existing

    import re
    import secrets
    base = re.sub(r"[^a-z0-9]+", "-", (name or user.email.split("@")[0]).lower()).strip("-") or "workspace"
    slug = f"{base[:55]}-{secrets.token_hex(4)}"
    organization = Organization(
        name=name or f"{user.name or user.email}'s workspace",
        slug=slug,
        webhook_token=secrets.token_urlsafe(24),
    )
    db.add(organization)
    await db.flush()
    db.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role=user.role))
    # Development migration path: assign only pre-multi-tenant demo records to
    # the first workspace created in this database. Production migrations should
    # instead map legacy records explicitly before enabling tenant enforcement.
    if settings.MOCK_MODE:
        from app.models import Customer, PaymentEvent, Case, StoppingRule
        for model in (Customer, PaymentEvent, Case, StoppingRule):
            await db.execute(update(model).where(model.organization_id.is_(None)).values(organization_id=organization.id))
    await db.flush()
    return organization


async def require_organization_admin(
    organization: Organization = Depends(get_current_organization),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    membership = await db.scalar(select(OrganizationMember).where(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == current_user.id,
    ))
    if not membership or membership.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace admin permission required")
    return organization
