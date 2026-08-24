"""
Database engine — auto-detects SQLite vs PostgreSQL from DATABASE_URL.
For local dev without Docker, uses SQLite (aiosqlite).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.core.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = {
    "echo": settings.DEBUG,
}

if _is_sqlite:
    # SQLite doesn't support pool_size / pool_pre_ping
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables():
    """Create all tables (used in development; production uses Alembic)."""
    from app.models import (  # noqa: F401
        customer, payment_event, case, diagnosis,
        intervention, outcome, audit_log, stopping_rule, user, organization
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
