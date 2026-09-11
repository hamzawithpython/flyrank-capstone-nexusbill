from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "nexusbill",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)

celery_app.conf.beat_schedule = {
    "rollup-usage-nightly": {
        "task": "rollup_usage",
        "schedule": crontab(hour=1, minute=0),
    },
}

# Imported at the bottom, after celery_app exists, so the task module's
# `from app.worker import celery_app` resolves without a circular import.
from app.core.jobs import rollup  # noqa: E402,F401