# ⚡ AI Revenue Recovery Platform

> **Razorpay Hackathon — Track 03** | AI-powered failed-payment recovery with full audit trails.

Built with FastAPI · React 18 · PostgreSQL · Redis · Celery · Claude AI (mocked by default)

---

## 🚀 Quick Start (Docker — recommended)

```bash
# 1. Clone / enter the project
cd lively-hertz

# 2. Start everything
docker compose up --build

# 3. Open the dashboard
open http://localhost

# 4. Login
#    Email: admin@demo.com  Password: demo1234
#    — or click "Continue with Google" (falls back to demo if Firebase not configured)

# 5. Click "Run Demo Replay" on the dashboard to process all 600 synthetic cases
```

The platform auto-seeds **60 Indian customers, 500 subscription failures, 100 invoice overdues, and 4 stopping rules** on first startup.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                React Frontend (MUI v6)           │
│  Dashboard · Cases · Escalations · Audit · Compliance │
└───────────────────┬─────────────────────────────┘
                    │ REST + JWT
┌───────────────────▼─────────────────────────────┐
│              FastAPI Backend (Python 3.11)       │
│  /api/v1: auth · cases · metrics · audit · ...  │
└──────┬────────────┬────────────┬────────────────┘
       │            │            │
  PostgreSQL     Redis       Celery Workers
  (SQLAlchemy)  (cache+MQ)  diagnosis → policy → execution → outcome
```

### AI Pipeline (per failed payment)

```
PaymentEvent → Diagnosis (Claude Haiku / rule-based)
             → Policy Engine (scored decision table)
             → Intervention (WhatsApp/SMS/Email/Voice message)
             → Outcome tracking + AuditLog (SHA-256 hash chain)
```

---

## 🎯 Key Features

| Feature | Detail |
|---------|--------|
| **Two-tier AI diagnosis** | Rule-based decline code mapping (70-97% confidence) → Claude Haiku LLM fallback |
| **Explainable policy engine** | Every action has a scored `expected_recovery_prob` + reasoning string |
| **Hinglish messaging** | WhatsApp/SMS/Email/Voice (TTS) messages in English + Hinglish |
| **HITL gate** | Cases > ₹10,000 or 3+ attempts auto-pause for human approval |
| **SHA-256 audit chain** | Every AI decision chained — tamper-evident for compliance |
| **Stopping rules** | TRAI quiet hours (9pm–9am), DND opt-out, cooldown, max-attempts |
| **MOCK_MODE** | Full demo with no real API keys needed |

---

## 🔧 Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Start PostgreSQL and Redis (or use Docker just for infra)
docker compose up db redis -d

# Copy env
copy .env .env.local   # edit as needed

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_MODE` | `true` | Skip real Razorpay/Claude calls |
| `DATABASE_URL` | postgres://... | Async SQLAlchemy URL |
| `SYNC_DATABASE_URL` | postgres://... | Sync URL for Celery workers |
| `REDIS_URL` | redis://... | Redis connection |
| `ANTHROPIC_API_KEY` | *(empty)* | Only needed when MOCK_MODE=false |
| `RAZORPAY_KEY_ID` | *(empty)* | Only needed when MOCK_MODE=false |
| `DEMO_ADMIN_EMAIL` | admin@demo.com | Demo login |
| `DEMO_ADMIN_PASSWORD` | demo1234 | Demo login |

## 🌐 Production multi-business setup

Each business has its own workspace, Razorpay webhook token, customers, cases,
compliance rules, and dashboard data.

1. Deploy behind HTTPS and set `MOCK_MODE=false`, a strong `SECRET_KEY`, plus
   explicit `ALLOWED_ORIGINS` and `ALLOWED_HOSTS` in `backend/.env`.
2. Run the schema migration: `alembic upgrade head`.
3. Sign in and open **Settings**. Create a workspace if prompted.
4. In **Razorpay connection**, save the business's key ID, key secret, and
   webhook signing secret. Copy the displayed unique webhook URL into Razorpay
   Dashboard → Webhooks and enable the failure events.
5. Optionally configure Resend (email), Twilio (SMS/WhatsApp), and a Slack
   incoming webhook for escalation alerts.

`POST /api/v1/payments/payment-links` creates a live Razorpay Payment Link
using the selected workspace's credentials.

> Before a public launch, replace database-stored integration secrets with a
> managed secret store/KMS and configure backups, monitoring, rate limiting,
> and your production domain values.

### Production verification checklist

```powershell
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
```

Use `/health` for liveness and `/ready` for database readiness. Configure the
Razorpay success and failure webhooks to the workspace URL shown in Settings;
events are deduplicated by their provider event ID. Configure Twilio's delivery
status callback to `/api/v1/webhooks/twilio/status/{workspace-webhook-token}`.

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | http://localhost:8000 | Backend URL |
| `VITE_FIREBASE_*` | *(empty)* | Only needed for real Google OAuth |

---

## 📊 Demo Walkthrough

1. **Login** → `admin@demo.com` / `demo1234`
2. **Dashboard** → Click `Run Demo Replay` at `10×` speed
3. Watch KPI cards and funnel fill in real-time (auto-refreshes every 2s)
4. **Cases** → Filter by `human_pending` → click Approve/Reject on escalated cases
5. **Case Detail** → See the full timeline: payment event → AI diagnosis → message sent with exact text → outcome
6. **"Why This Action?"** panel → every scored option with expected recovery probability
7. **Audit Trail** → Select any case → verify SHA-256 chain integrity with one click
8. **Compliance** → Edit stopping rules, see DND list, manage escalation queue

---

## 📁 Project Structure

```
lively-hertz/
├── docker-compose.yml
├── nginx.conf
├── backend/
│   ├── app/
│   │   ├── core/           config, database, auth, redis
│   │   ├── models/         SQLAlchemy ORM models (9 tables)
│   │   ├── schemas/        Pydantic request/response schemas
│   │   ├── routers/        FastAPI route handlers (9 routers)
│   │   ├── services/
│   │   │   └── ai/         root_cause_classifier, policy_engine,
│   │   │                   message_generator, promise_tracker
│   │   ├── workers/        Celery: diagnosis→policy→execution→outcome
│   │   └── seed/           60 customers, 600 synthetic failures
│   ├── alembic/            DB migrations
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── api/            Axios client + typed API functions
    │   ├── auth/           Firebase OAuth + email/password
    │   ├── components/     Layout, charts, shared UI
    │   ├── pages/          Dashboard, Cases, CaseDetail,
    │   │                   Escalations, Compliance, AuditTrail
    │   ├── store/          Zustand auth + replay stores
    │   └── theme/          MUI v6 Razorpay theme + constants
    └── Dockerfile
```

---

## 🧪 API Reference

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: GET http://localhost:8000/health

Key endpoints:
```
POST /api/v1/auth/login          # Email login
POST /api/v1/auth/google         # Firebase OAuth
GET  /api/v1/cases               # List with filters/pagination
GET  /api/v1/cases/{id}          # Full case detail + timeline
POST /api/v1/cases/{id}/approve  # HITL approve
GET  /api/v1/metrics/overview    # KPI dashboard
GET  /api/v1/metrics/funnel      # Recovery funnel data
GET  /api/v1/audit/{case_id}     # Hash-chained audit log
GET  /api/v1/audit/{id}/verify   # Chain integrity check
POST /api/v1/replay/start        # Trigger batch pipeline
POST /api/v1/webhooks/razorpay   # Ingest failure events
```

---

## ⚠️ Production Checklist

- [ ] Set `MOCK_MODE=false`
- [ ] Set real `ANTHROPIC_API_KEY`, `RAZORPAY_*`, Firebase config
- [ ] Change `SECRET_KEY` to a cryptographically random value
- [ ] Use Alembic for all DB changes (not `create_all`)
- [ ] Enable HTTPS / TLS termination
- [ ] Add rate limiting on webhook endpoint
- [ ] Set up proper logging / error tracking (Sentry)

---

*Built for Razorpay Hackathon 2026 · Track 03 · AI Revenue Recovery*
