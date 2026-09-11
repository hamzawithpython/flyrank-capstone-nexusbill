import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from app.db import get_session
from app.models import StripeWebhookEvent
from app.core.stripe.event_router import EVENT_HANDLERS

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
MAX_ATTEMPTS = 3


@router.post("/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    existing = session.exec(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event["id"])
    ).first()

    if existing is not None:
        if existing.status == "processed":
            # Genuinely already handled — this is Stripe's real dedup case.
            return {"received": True, "duplicate": True}
        if existing.status == "failed":
            # Already exhausted retries and dead-lettered — don't silently
            # reprocess automatically. Needs an explicit admin retry (M5).
            return {"received": True, "dead_lettered": True}
        # status == "pending": received before but never finished — retry
        # it now instead of treating a stuck event as a duplicate forever.
        record = existing
    else:
        record = StripeWebhookEvent(
            stripe_event_id=event["id"],
            event_type=event["type"],
            payload=json.loads(raw_body),
            status="pending",
        )
        session.add(record)
        session.commit()
        session.refresh(record)

    handler = EVENT_HANDLERS.get(event["type"])
    if handler is None:
        record.status = "processed"
        record.processed_at = datetime.utcnow()
        session.add(record)
        session.commit()
        return {"received": True, "handled": False}

    try:
        handler(event["data"]["object"], session)
        record.status = "processed"
        record.processed_at = datetime.utcnow()
        session.add(record)
        session.commit()
    except Exception as e:
        session.rollback()
        record.attempts += 1
        record.last_error = str(e)
        if record.attempts >= MAX_ATTEMPTS:
            record.status = "failed"
        session.add(record)
        session.commit()
        return {"received": True, "processing_error": True}

    return {"received": True, "handled": True}