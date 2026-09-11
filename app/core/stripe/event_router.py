from datetime import datetime
from sqlmodel import Session, select
from app.models import Organization, Plan, Subscription, AuditLog


def _get_plan_by_name(name: str, session: Session) -> Plan:
    return session.exec(select(Plan).where(Plan.name == name)).first()


def handle_checkout_completed(event_data: dict, session: Session) -> None:
    event_data = event_data.to_dict() if hasattr(event_data, "to_dict") else event_data
    metadata = event_data.get("metadata", {})
    org_id = metadata.get("org_id")
    target_plan_name = metadata.get("target_plan")
    if not org_id or not target_plan_name:
        raise ValueError("checkout.session.completed missing org_id/target_plan metadata")

    org = session.get(Organization, org_id)
    plan = _get_plan_by_name(target_plan_name, session)
    if org is None or plan is None:
        raise ValueError(f"Unknown org {org_id} or plan {target_plan_name}")

    stripe_subscription_id = event_data.get("subscription")

    existing_sub = session.exec(
        select(Subscription).where(Subscription.org_id == org.id)
    ).first()
    if existing_sub:
        existing_sub.plan_id = plan.id
        existing_sub.stripe_subscription_id = stripe_subscription_id
        existing_sub.status = "active"
        session.add(existing_sub)
    else:
        session.add(Subscription(
            org_id=org.id, plan_id=plan.id,
            stripe_subscription_id=stripe_subscription_id, status="active",
        ))

    org.plan_id = plan.id
    session.add(org)

    session.add(AuditLog(
        org_id=org.id, actor="stripe-webhook", event_type="plan.upgraded",
        payload={"new_plan": target_plan_name, "stripe_subscription_id": stripe_subscription_id},
    ))


def handle_subscription_updated(event_data: dict, session: Session) -> None:
    stripe_sub_id = event_data.get("id")
    sub = session.exec(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    ).first()
    if sub is None:
        raise ValueError(f"No local subscription found for Stripe subscription {stripe_sub_id}")

    # Out-of-order guard: Stripe doesn't guarantee delivery order. If this
    # event's period_start is not newer than what we already have, a LATER
    # event already applied more current state — skip, don't overwrite it.
    new_period_start = event_data.get("current_period_start")
    if sub.current_period_start and new_period_start:
        new_start_dt = datetime.utcfromtimestamp(new_period_start)
        if new_start_dt <= sub.current_period_start:
            return  # stale event, silently skip

    sub.status = event_data.get("status", sub.status)
    if new_period_start:
        sub.current_period_start = datetime.utcfromtimestamp(new_period_start)
    if event_data.get("current_period_end"):
        sub.current_period_end = datetime.utcfromtimestamp(event_data["current_period_end"])
    session.add(sub)

    session.add(AuditLog(
        org_id=sub.org_id, actor="stripe-webhook", event_type="subscription.updated",
        payload={"status": sub.status},
    ))


def handle_subscription_deleted(event_data: dict, session: Session) -> None:
    stripe_sub_id = event_data.get("id")
    sub = session.exec(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    ).first()
    if sub is None:
        raise ValueError(f"No local subscription found for Stripe subscription {stripe_sub_id}")

    free_plan = _get_plan_by_name("free", session)
    sub.status = "cancelled"
    sub.cancelled_at = datetime.utcnow()
    session.add(sub)

    org = session.get(Organization, sub.org_id)
    org.plan_id = free_plan.id
    session.add(org)

    session.add(AuditLog(
        org_id=org.id, actor="stripe-webhook", event_type="plan.downgraded",
        payload={"reason": "subscription_deleted", "new_plan": "free"},
    ))


def handle_payment_failed(event_data: dict, session: Session) -> None:
    stripe_customer_id = event_data.get("customer")
    org = session.exec(
        select(Organization).where(Organization.stripe_customer_id == stripe_customer_id)
    ).first()
    if org is None:
        raise ValueError(f"No org found for Stripe customer {stripe_customer_id}")

    org.status = "past_due"
    session.add(org)

    session.add(AuditLog(
        org_id=org.id, actor="stripe-webhook", event_type="payment.failed", payload={},
    ))


EVENT_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.payment_failed": handle_payment_failed,
}