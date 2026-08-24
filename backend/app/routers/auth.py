"""
Auth router — Supabase OAuth + email/password login (with demo fallback).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import httpx

from app.core.database import get_db
from app.core.auth import create_access_token, verify_password, get_password_hash, get_current_user
from app.core.config import settings
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.core.tenancy import ensure_personal_organization
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


class SupabaseAuthRequest(BaseModel):
    access_token: str


async def _verify_supabase_access_token(access_token: str) -> dict:
    """Validate a Supabase session with Supabase Auth and return its user."""
    api_key = settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_ANON_KEY
    if not settings.SUPABASE_URL or not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {access_token}", "apikey": api_key},
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase token") from exc


async def _get_or_create_user(
    db: AsyncSession, email: str, name: str, photo_url: Optional[str] = None
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.last_login = datetime.utcnow()
        if name and not user.name:
            user.name = name
        await ensure_personal_organization(db, user)
        return user
    new_user = User(
        id=uuid.uuid4(),
        email=email,
        name=name or email.split("@")[0],
        photo_url=photo_url,
        role=UserRole.admin,
        last_login=datetime.utcnow(),
    )
    db.add(new_user)
    await db.flush()
    await ensure_personal_organization(db, new_user)
    return new_user


# ── Supabase token exchange ──
@router.post("/supabase", response_model=TokenResponse)
async def supabase_auth(request: SupabaseAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Exchange a Supabase JWT for our app token (or pass through if JWT secret matches).
    Called by the frontend after a successful Supabase sign-in.
    """
    payload = await _verify_supabase_access_token(request.access_token)
    email = payload.get("email") or payload.get("id", "")
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase account has no email address")
    metadata = payload.get("user_metadata", {})
    name = metadata.get("full_name", "") if isinstance(metadata, dict) else ""
    photo_url = metadata.get("avatar_url") if isinstance(metadata, dict) else None

    user = await _get_or_create_user(db, email, name or email.split("@")[0], photo_url)
    await db.commit()
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return TokenResponse(
        access_token=token, user_id=str(user.id),
        email=user.email, name=user.name, role=user.role,
    )


# ── Email / password ──
@router.post("/login", response_model=TokenResponse)
async def email_login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Email/password login. Demo: admin@demo.com / demo1234"""
    # Demo shortcut
    if (request.email == settings.DEMO_ADMIN_EMAIL
            and request.password == settings.DEMO_ADMIN_PASSWORD):
        user = await _get_or_create_user(db, settings.DEMO_ADMIN_EMAIL, "Demo Admin")
        user.role = UserRole.admin
        await db.commit()
        token = create_access_token(data={"sub": user.email, "role": user.role.value})
        return TokenResponse(
            access_token=token, user_id=str(user.id),
            email=user.email, name=user.name, role=user.role,
        )

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    await db.commit()
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return TokenResponse(
        access_token=token, user_id=str(user.id),
        email=user.email, name=user.name, role=user.role,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create an organization owner account for local email/password use."""
    email = request.email.strip().lower()
    if len(request.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        id=uuid.uuid4(), email=email, name=request.name.strip() or email.split("@")[0],
        hashed_password=get_password_hash(request.password), role=UserRole.admin,
        last_login=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    await ensure_personal_organization(db, user)
    await db.commit()
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return TokenResponse(access_token=token, user_id=str(user.id), email=user.email, name=user.name, role=user.role)


# ── Me ──
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
