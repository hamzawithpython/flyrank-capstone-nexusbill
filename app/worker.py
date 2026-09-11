from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "nexusbill",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)

celery_app.conf.beat_schedule = {
    "rollup-usage-nightly": {"task": "rollup_usage", "schedule": crontab(hour=1, minute=0)},
    "reconcile-stripe-nightly": {"task": "reconcile_stripe", "schedule": crontab(hour=2, minute=0)},
}

from app.core.jobs import rollup, alerts, reconciliation  # noqa: E402,F401