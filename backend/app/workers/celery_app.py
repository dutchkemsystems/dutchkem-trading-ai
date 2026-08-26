"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "dutchkem_fortress",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
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
    beat_schedule={
        "fetch-fx-rates": {
            "task": "app.workers.tasks.fetch_fx_rates",
            "schedule": crontab(minute="*/15"),
        },
        "check-low-balances": {
            "task": "app.workers.tasks.check_low_balances",
            "schedule": crontab(hour="*/1"),
        },
        "generate-daily-invoices": {
            "task": "app.workers.tasks.generate_daily_invoices",
            "schedule": crontab(hour=1, minute=0),
        },
    },
)
