from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from app.models import UsageEvent, Plan, Organization


def check_quota(org: Organization, plan: Plan, this_request_tokens: int, session: Session):
    period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    call_count, token_count = session.exec(
        select(
            func.count(UsageEvent.id),
            func.coalesce(func.sum(
                UsageEvent.input_tokens + UsageEvent.cached_input_tokens
                + UsageEvent.output_tokens + UsageEvent.reasoning_tokens
            ), 0),
        ).where(UsageEvent.org_id == org.id, UsageEvent.created_at >= period_start)
    ).first()

    if plan.api_call_quota != -1 and (call_count + 1) > plan.api_call_quota:
        raise HTTPException(
            status_code=429,
            detail={"error": "api_call_quota_exceeded", "message": "API call quota exceeded for this billing period.",
                    "quota": plan.api_call_quota, "used": call_count, "usage_type": "api_calls"},
        )

    if plan.token_quota != -1 and (token_count + this_request_tokens) > plan.token_quota:
        raise HTTPException(
            status_code=429,
            detail={"error": "token_quota_exceeded", "message": "Token quota exceeded for this billing period.",
                    "quota": plan.token_quota, "used": token_count, "this_request": this_request_tokens, "usage_type": "tokens"},
        )

    return call_count, token_count