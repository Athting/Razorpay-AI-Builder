from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

from app.models.user import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str
    role: UserRole


class GoogleAuthRequest(BaseModel):
    id_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(LoginRequest):
    name: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    photo_url: Optional[str] = None
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
