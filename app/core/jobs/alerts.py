from datetime import date
from sqlmodel import Session, select
from app.db import engine
from app.worker import celery_app
from app.models import UsageAlert


@celery_app.task(name="send_quota_alert")
def send_quota_alert(org_id: str, alert_type: str, usage_type: str):
    """alert_type: 'quota_80' | 'quota_100'. usage_type: 'api_calls' | 'tokens'.
    Idempotent per (org, alert_type, usage_type, period) via the UNIQUE
    constraint already in the M0 schema — safe to call more than once
    without double-alerting in the same billing period."""
    period_start = date.today().replace(day=1)
    with Session(engine) as session:
        existing = session.exec(
            select(UsageAlert).where(
                UsageAlert.org_id == org_id,
                UsageAlert.alert_type == alert_type,
                UsageAlert.usage_type == usage_type,
                UsageAlert.period_start == period_start,
            )
        ).first()
        if existing:
            return {"already_sent": True}

        session.add(UsageAlert(
            org_id=org_id, alert_type=alert_type, usage_type=usage_type,
            period_start=period_start,
        ))
        session.commit()
        # Mock notification — a real system would email/Slack here.
        print(f"[ALERT] org={org_id} {alert_type} {usage_type} threshold crossed")

    return {"sent": True}