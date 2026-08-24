"""
FastAPI application entry point — AI Revenue Recovery Platform.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.rate_limit import RateLimitMiddleware

from app.core.config import settings
from app.core.database import create_all_tables
from app.routers import auth, cases, metrics, audit, stopping_rules, replay, webhooks, customers, interventions, organizations, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Create tables
    await create_all_tables()

    # Seed demo data if MOCK_MODE
    if settings.MOCK_MODE:
        try:
            from app.core.database import AsyncSessionLocal
            from app.seed.synthetic_data import seed_all
            async with AsyncSessionLocal() as db:
                result = await seed_all(db)
                print(f"[Seed] {result}")
        except Exception as e:
            print(f"[Seed] Skipped or already seeded: {e}")

    yield
    # Shutdown
    from app.core.redis import close_redis
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered revenue recovery platform — detects, diagnoses, decides, acts, and audits.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# Configure ALLOWED_HOSTS with your public domain in production.
if not settings.DEBUG:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Routers
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(cases.router, prefix=API_PREFIX)
app.include_router(metrics.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(stopping_rules.router, prefix=API_PREFIX)
app.include_router(replay.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(customers.router, prefix=API_PREFIX)
app.include_router(interventions.router, prefix=API_PREFIX)
app.include_router(organizations.router, prefix=API_PREFIX)
app.include_router(payments.router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "mock_mode": settings.MOCK_MODE}


@app.get("/ready")
async def ready():
    """Readiness endpoint for load balancers and deployment monitoring."""
    from sqlalchemy import text
    from app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/api/v1/seed")
async def trigger_seed():
    """Manually re-seed the database (MOCK_MODE only)."""
    if not settings.MOCK_MODE:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Seeding only available in MOCK_MODE")
    from app.core.database import AsyncSessionLocal
    from app.seed.synthetic_data import seed_all
    async with AsyncSessionLocal() as db:
        result = await seed_all(db)
    return result
