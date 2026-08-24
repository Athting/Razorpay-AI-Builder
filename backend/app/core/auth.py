"""
Auth core — supports Supabase JWTs and local JWTs (fallback).
- Supabase tokens are verified through its JWKS endpoint (ES256).
- Legacy Supabase HS256 JWTs and local JWTs remain supported.
"""
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

import httpx

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@lru_cache(maxsize=1)
def _get_supabase_jwks() -> dict:
    """Retrieve and cache Supabase's public ES256 signing keys."""
    try:
        response = httpx.get(settings.SUPABASE_JWKS_URL, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise JWTError("Unable to load Supabase signing keys") from exc


def _decode_supabase_jwks_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "ES256":
            raise JWTError("Unexpected Supabase JWT algorithm")

        key_id = header.get("kid")
        keys = _get_supabase_jwks().get("keys", [])
        signing_key = next((key for key in keys if key.get("kid") == key_id), None)
        if signing_key is None:
            # A signing-key rotation may have occurred since the cache was populated.
            _get_supabase_jwks.cache_clear()
            keys = _get_supabase_jwks().get("keys", [])
            signing_key = next((key for key in keys if key.get("kid") == key_id), None)
        if signing_key is None:
            raise JWTError("Supabase signing key was not found")

        return jwt.decode(
            token,
            signing_key,
            algorithms=["ES256"],
            issuer=f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
            options={"verify_aud": False},
        )
    except (JWTError, KeyError, TypeError) as exc:
        raise JWTError("Invalid Supabase token") from exc


def _decode_token(token: str) -> dict:
    """
    Try current Supabase JWKS verification, legacy Supabase verification,
    then fall back to our own local HS256 token.
    """
    if settings.SUPABASE_JWKS_URL and settings.SUPABASE_URL:
        try:
            return _decode_supabase_jwks_token(token)
        except JWTError:
            pass

    # Try Supabase secret
    if settings.SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            pass

    # Fall back to local secret
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def _extract_email_from_payload(payload: dict) -> Optional[str]:
    """
    Supabase tokens store email in payload['email'] or payload['sub'] (UUID).
    Our tokens store email in payload['sub'].
    """
    email = payload.get("email")
    if email:
        return email
    sub = payload.get("sub", "")
    # If sub looks like an email (not a UUID), use it
    if sub and "@" in sub:
        return sub
    return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """FastAPI dependency: decode JWT and return the User ORM object."""
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = _decode_token(token)
        email = _extract_email_from_payload(payload)
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Same as get_current_user but returns None instead of raising."""
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
