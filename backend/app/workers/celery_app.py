from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "revenue_recovery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.diagnosis_worker",
        "app.workers.policy_worker",
        "app.workers.execution_worker",
        "app.workers.outcome_listener",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.diagnosis_worker.*": {"queue": "diagnosis"},
        "app.workers.policy_worker.*": {"queue": "policy"},
        "app.workers.execution_worker.*": {"queue": "execution"},
        "app.workers.outcome_listener.*": {"queue": "outcomes"},
    },
)
