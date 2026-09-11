from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.deps import get_caller_org
from app.core.stripe.event_router import EVENT_HANDLERS
from app.core.jobs.reconciliation import reconcile_stripe
from app.db import get_session
from app.models import ReconciliationReport, StripeWebhookEvent

router = APIRouter(prefix="/admin", tags=["admin"])

# NOTE — scope limitation, documented deliberately: these routes require
# only ordinary authentication (any org owner's JWT), not a genuine
# platform-admin role. No is_platform_admin concept exists in this schema.
# A real production system needs a separate staff/admin identity, distinct
# from customer accounts — these endpoints currently see ALL orgs' data,
# not just the caller's own.


@router.post("/reconcile")
def trigger_reconcile(org=Depends(get_caller_org)):
    # Called directly, not via .delay() — an admin manually triggering this
    # wants the result immediately, unlike the nightly scheduled run.
    return reconcile_stripe()


@router.get("/reconciliation-reports")
def list_reconciliation_reports(
    limit: int = 10,
    org=Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    return session.exec(
        select(ReconciliationReport).order_by(ReconciliationReport.run_at.desc()).limit(limit)
    ).all()


@router.get("/failed-webhooks")
def list_failed_webhooks(
    org=Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    return session.exec(
        select(StripeWebhookEvent).where(StripeWebhookEvent.status == "failed")
    ).all()


@router.post("/failed-webhooks/{event_id}/retry")
def retry_failed_webhook(
    event_id: UUID,
    org=Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    event = session.get(StripeWebhookEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    if event.status != "failed":
        raise HTTPException(status_code=400, detail=f"Event status is '{event.status}', not 'failed'")

    handler = EVENT_HANDLERS.get(event.event_type)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"No handler registered for {event.event_type}")

    try:
        # Reprocess using the ORIGINALLY STORED payload. Stripe never
        # redelivers a dead-lettered event on its own — the webhook route
        # always returns 200 even on failure (M4's design, so our own
        # retry logic never races Stripe's). This admin action is the
        # only path back for a dead-lettered event short of manually
        # running `stripe events resend`.
        handler(event.payload["data"]["object"], session)
        event.status = "processed"
        event.processed_at = datetime.utcnow()
        event.last_error = None
        session.add(event)
        session.commit()
        return {"message": "Retry succeeded", "status": "processed"}
    except Exception as e:
        session.rollback()
        event.attempts += 1
        event.last_error = str(e)
        session.add(event)
        session.commit()
        return {"message": "Retry failed again", "status": event.status, "error": str(e)}