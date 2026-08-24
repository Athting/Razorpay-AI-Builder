"""Workspace onboarding and secure integration configuration."""
from pydantic import BaseModel, Field, EmailStr
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from jose import jwt, JWTError
from datetime import datetime, timedelta
import httpx
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.tenancy import get_current_organization, ensure_personal_organization, require_organization_admin
from app.models.organization import Organization
from app.models.organization import OrganizationMember
from app.models.user import User, UserRole
from sqlalchemy import select
from app.core.secrets import seal, unseal

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class RazorpayConfig(BaseModel):
    key_id: str = Field(min_length=5, max_length=255)
    key_secret: str = Field(min_length=5, max_length=255)
    webhook_secret: str = Field(min_length=5, max_length=255)


class NotificationConfig(BaseModel):
    email_recipients: list[str] = []
    slack_webhook_url: str | None = None
    escalation_alerts: bool = True


class CommunicationConfig(BaseModel):
    """Provider credentials are write-only. Never return this configuration."""
    resend_api_key: str | None = None
    sender_email: EmailStr | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    twilio_whatsapp_from: str | None = None

class MemberChange(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.viewer

class MemberRoleChange(BaseModel):
    role: UserRole


def serialize(org: Organization) -> dict:
    return {
        "id": str(org.id), "name": org.name, "slug": org.slug,
        "webhook_path": f"/api/v1/webhooks/razorpay/{org.webhook_token}",
        "razorpay_connected": bool(org.razorpay_key_id or org.razorpay_oauth_config),
        "notification_config": org.notification_config or {},
    }


@router.post("", status_code=201)
async def create_organization(payload: OrganizationCreate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    organization = await ensure_personal_organization(db, current_user, payload.name)
    return serialize(organization)


@router.get("/current")
async def current_organization(organization: Organization = Depends(get_current_organization)):
    return serialize(organization)


@router.get("")
async def list_organizations(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Organization).join(OrganizationMember).where(OrganizationMember.user_id == current_user.id, Organization.is_active.is_(True)))
    return [serialize(org) for org in result.scalars().all()]


@router.get("/current/members")
async def list_members(organization: Organization = Depends(get_current_organization), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrganizationMember, User).join(User).where(OrganizationMember.organization_id == organization.id))
    return [{"id": str(m.id), "user_id": str(u.id), "email": u.email, "name": u.name, "role": m.role.value} for m, u in result.all()]


@router.post("/current/members", status_code=201)
async def add_member(payload: MemberChange, organization: Organization = Depends(require_organization_admin), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == str(payload.email)))
    if not user:
        raise HTTPException(status_code=404, detail="User must sign in once before being added")
    existing = await db.scalar(select(OrganizationMember).where(OrganizationMember.organization_id == organization.id, OrganizationMember.user_id == user.id))
    if existing:
        raise HTTPException(status_code=409, detail="User is already a workspace member")
    member = OrganizationMember(organization_id=organization.id, user_id=user.id, role=payload.role)
    db.add(member)
    return {"id": str(member.id), "email": user.email, "role": member.role.value}


@router.put("/current/members/{member_id}")
async def update_member(member_id: str, payload: MemberRoleChange, organization: Organization = Depends(require_organization_admin), db: AsyncSession = Depends(get_db)):
    member = await db.scalar(select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.organization_id == organization.id))
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = payload.role
    return {"status": "updated"}


@router.delete("/current/members/{member_id}", status_code=204)
async def remove_member(member_id: str, organization: Organization = Depends(require_organization_admin), db: AsyncSession = Depends(get_db)):
    member = await db.scalar(select(OrganizationMember).where(OrganizationMember.id == member_id, OrganizationMember.organization_id == organization.id))
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)


@router.put("/current/razorpay")
async def configure_razorpay(payload: RazorpayConfig, organization: Organization = Depends(require_organization_admin)):
    # Secrets are never returned by this API. Use a KMS/envelope encryption layer before production launch.
    # Preserve legacy columns for compatibility; sensitive values are sealed.
    organization.razorpay_key_id = payload.key_id
    organization.razorpay_key_secret = None
    organization.razorpay_webhook_secret = None
    organization.razorpay_oauth_config = seal({"auth_type": "key_secret", "key_secret": payload.key_secret, "webhook_secret": payload.webhook_secret})
    return {"status": "connected", "webhook_path": f"/api/v1/webhooks/razorpay/{organization.webhook_token}"}


@router.put("/current/notifications")
async def configure_notifications(payload: NotificationConfig, organization: Organization = Depends(require_organization_admin)):
    organization.notification_config = payload.model_dump(exclude_none=True)
    return {"status": "updated", "notification_config": organization.notification_config}


@router.put("/current/communications")
async def configure_communications(payload: CommunicationConfig, organization: Organization = Depends(require_organization_admin)):
    organization.communication_config = seal(payload.model_dump(exclude_none=True))
    return {"status": "updated", "configured_channels": {
        "email": bool(organization.communication_config.get("resend_api_key") and organization.communication_config.get("sender_email")),
        "sms": bool(organization.communication_config.get("twilio_account_sid") and organization.communication_config.get("twilio_from_number")),
        "whatsapp": bool(organization.communication_config.get("twilio_account_sid") and organization.communication_config.get("twilio_whatsapp_from")),
    }}


@router.get("/current/razorpay/connect")
async def razorpay_connect_url(organization: Organization = Depends(require_organization_admin)):
    if not all([settings.RAZORPAY_OAUTH_CLIENT_ID, settings.RAZORPAY_OAUTH_CLIENT_SECRET, settings.RAZORPAY_OAUTH_REDIRECT_URI]):
        raise HTTPException(status_code=503, detail="Razorpay Partner OAuth is not configured on this deployment")
    state = jwt.encode({"org": str(organization.id), "exp": datetime.utcnow() + timedelta(minutes=10)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"url": "https://auth.razorpay.com/authorize?" + urlencode({"client_id": settings.RAZORPAY_OAUTH_CLIENT_ID, "response_type": "code", "redirect_uri": settings.RAZORPAY_OAUTH_REDIRECT_URI, "scope": "read_write", "state": state})}


@router.get("/razorpay/callback", include_in_schema=False)
async def razorpay_oauth_callback(code: str, state: str):
    try:
        organization_id = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["org"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://auth.razorpay.com/token", json={"client_id": settings.RAZORPAY_OAUTH_CLIENT_ID, "client_secret": settings.RAZORPAY_OAUTH_CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": settings.RAZORPAY_OAUTH_REDIRECT_URI})
    if response.is_error:
        raise HTTPException(status_code=502, detail="Razorpay OAuth token exchange failed")
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        org = await db.get(Organization, organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Workspace not found")
        org.razorpay_oauth_config = seal({"auth_type": "oauth", **response.json()})
        await db.commit()
    return RedirectResponse(url="/settings?razorpay=connected", status_code=303)


@router.post("/current/razorpay/refresh")
async def refresh_razorpay_oauth(organization: Organization = Depends(require_organization_admin)):
    credentials = unseal(organization.razorpay_oauth_config)
    if credentials.get("auth_type") != "oauth" or not credentials.get("refresh_token"):
        raise HTTPException(status_code=409, detail="No Razorpay OAuth refresh token is connected")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post("https://auth.razorpay.com/token", json={"client_id": settings.RAZORPAY_OAUTH_CLIENT_ID, "client_secret": settings.RAZORPAY_OAUTH_CLIENT_SECRET, "grant_type": "refresh_token", "refresh_token": credentials["refresh_token"]})
    if response.is_error:
        raise HTTPException(status_code=502, detail="Razorpay OAuth refresh failed")
    organization.razorpay_oauth_config = seal({"auth_type": "oauth", **response.json()})
    return {"status": "refreshed"}
