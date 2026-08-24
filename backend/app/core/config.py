from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    # ─── Database ───
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/revenue_recovery"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/revenue_recovery"

    # ─── Redis / Celery ───
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # ─── Supabase (optional) ───
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""  # From Supabase Dashboard → Project Settings → API → JWT Secret
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_JWKS_URL: str = ""

    # ─── Auth (local fallback when Supabase not configured) ───
    SECRET_KEY: str = "supersecretkey-change-in-production-abc123xyz"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ─── Google Gemini AI ───
    GEMINI_API_KEY: str = ""
    MOCK_MODE: bool = True  # True = no external AI/payment calls

    # ─── Razorpay (optional) ───
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_OAUTH_CLIENT_ID: str = ""
    RAZORPAY_OAUTH_CLIENT_SECRET: str = ""
    RAZORPAY_OAUTH_REDIRECT_URI: str = ""

    # Encrypt per-workspace provider credentials at rest. Set this to a
    # durable 32-byte URL-safe base64 key in production.
    INTEGRATION_ENCRYPTION_KEY: str = ""
    RATE_LIMIT_PER_MINUTE: int = 120

    # ─── CORS ───
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
    ]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # ─── App ───
    APP_NAME: str = "AI Revenue Recovery"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug_value(cls, value):
        """Accept common deployment labels while retaining a boolean setting."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev", "debug"}:
                return True
        return value

    # ─── Demo credentials ───
    DEMO_ADMIN_EMAIL: str = "admin@demo.com"
    DEMO_ADMIN_PASSWORD: str = "demo1234"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and (self.SUPABASE_PUBLISHABLE_KEY or self.SUPABASE_ANON_KEY))

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and not self.MOCK_MODE)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
