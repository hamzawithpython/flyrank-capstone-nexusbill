from datetime import date, datetime, timedelta
from sqlmodel import Session, select
from sqlalchemy import func
from app.db import engine
from app.worker import celery_app
from app.models import Organization, UsageEvent, UsageRollup


@celery_app.task(name="rollup_usage")
def rollup_usage():
    """Aggregates the current calendar month's usage_events into one
    usage_rollups row per organization. Idempotent — re-running for the
    same period (which nightly execution does every night) updates the
    existing row via the UNIQUE(org_id, period_start) constraint rather
    than duplicating it."""
    period_start = date.today().replace(day=1)
    if period_start.month == 12:
        period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

    with Session(engine) as session:
        orgs = session.exec(select(Organization)).all()
        for org in orgs:
            agg = session.exec(
                select(
                    func.count(UsageEvent.id),
                    func.coalesce(func.sum(UsageEvent.input_tokens), 0),
                    func.coalesce(func.sum(UsageEvent.cached_input_tokens), 0),
                    func.coalesce(func.sum(UsageEvent.output_tokens), 0),
                    func.coalesce(func.sum(UsageEvent.reasoning_tokens), 0),
                    func.coalesce(func.sum(UsageEvent.total_cost_micros), 0),
                ).where(
                    UsageEvent.org_id == org.id,
                    UsageEvent.created_at >= period_start,
                )
            ).first()

            api_calls, input_t, cached_t, output_t, reasoning_t, cost = agg

            existing = session.exec(
                select(UsageRollup).where(
                    UsageRollup.org_id == org.id,
                    UsageRollup.period_start == period_start,
                )
            ).first()

            if existing:
                existing.period_end = period_end
                existing.api_calls = api_calls
                existing.input_tokens = input_t
                existing.cached_input_tokens = cached_t
                existing.output_tokens = output_t
                existing.reasoning_tokens = reasoning_t
                existing.total_cost_micros = cost
                existing.computed_at = datetime.utcnow()
                session.add(existing)
            else:
                session.add(UsageRollup(
                    org_id=org.id, period_start=period_start, period_end=period_end,
                    api_calls=api_calls, input_tokens=input_t, cached_input_tokens=cached_t,
                    output_tokens=output_t, reasoning_tokens=reasoning_t, total_cost_micros=cost,
                ))
        session.commit()

    return {"orgs_processed": len(orgs)}