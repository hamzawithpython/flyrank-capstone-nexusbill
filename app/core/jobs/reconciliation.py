import os
import stripe
from sqlmodel import Session, select
from app.db import engine
from app.worker import celery_app
from app.models import Organization, Subscription, ReconciliationReport, AuditLog

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


@celery_app.task(name="reconcile_stripe")
def reconcile_stripe():
    """Compares each org's local subscription record against Stripe's own
    view of it. Local state can drift from Stripe's if a webhook was ever
    missed, delayed, or mishandled — this is the safety net that catches
    that drift independently of the webhook path itself."""
    with Session(engine) as session:
        orgs = session.exec(
            select(Organization).where(Organization.stripe_customer_id != None)
        ).all()

        mismatches = []
        for org in orgs:
            sub = session.exec(select(Subscription).where(Subscription.org_id == org.id)).first()
            if sub is None or sub.stripe_subscription_id is None:
                continue

            try:
                stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
            except stripe.error.StripeError as e:
                mismatches.append({"org_id": str(org.id), "error": str(e)})
                continue

            if stripe_sub.status != sub.status:
                mismatches.append({
                    "org_id": str(org.id), "field": "status",
                    "local": sub.status, "stripe": stripe_sub.status,
                })

        status = "has_mismatches" if mismatches else "clean"
        report = ReconciliationReport(
            orgs_checked=len(orgs), mismatches=mismatches or None, status=status,
        )
        session.add(report)

        if mismatches:
            session.add(AuditLog(
                actor="system", event_type="reconciliation.mismatch_found",
                payload={"mismatches": mismatches},
            ))
        session.commit()

    return {"status": status, "orgs_checked": len(orgs), "mismatch_count": len(mismatches)}