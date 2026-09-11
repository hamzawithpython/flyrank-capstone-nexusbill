from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.deps import get_caller_org
from app.core.billing.calculator import calculate_cost_micros
from app.db import get_session
from app.models import Organization, Plan, AIModel
from app.schemas.estimate import EstimateRequest

router = APIRouter(prefix="/billing", tags=["billing"])


def _fmt_dollars(micros: int) -> str:
    return f"${micros / 1_000_000:.2f}"


@router.post("/estimate")
def estimate(
    payload: EstimateRequest,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(AIModel).where(AIModel.slug == payload.model, AIModel.is_active == True)
    ).first()
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown or inactive model: {payload.model}")

    estimated_requests = payload.daily_requests * payload.days
    total_input = payload.avg_input_tokens * estimated_requests
    total_cached = payload.avg_cached_input_tokens * estimated_requests
    total_output = payload.avg_output_tokens * estimated_requests
    total_reasoning = payload.avg_reasoning_tokens * estimated_requests

    # Each cost isolated to its own CostCalculator call, one token type at a
    # time — reused exactly as-is from M2, no new pricing logic written here.
    # This deliberately trades a few negligible micros of extra truncation
    # (at most ~3, against totals in the hundreds of dollars) for matching
    # the response shape's four separate line items directly.
    input_cost = calculate_cost_micros(total_input, 0, 0, 0, model.input_price_per_1m_micros, 0, 0, 0)
    cached_cost = calculate_cost_micros(0, total_cached, 0, 0, 0, model.cached_input_price_per_1m_micros, 0, 0)
    output_cost = calculate_cost_micros(0, 0, total_output, 0, 0, 0, model.output_price_per_1m_micros, 0)
    reasoning_cost = calculate_cost_micros(0, 0, 0, total_reasoning, 0, 0, 0, model.reasoning_price_per_1m_micros)
    total_cost = input_cost + cached_cost + output_cost + reasoning_cost

    current_plan = session.get(Plan, org.plan_id)
    total_tokens = total_input + total_cached + total_output + total_reasoning

    recommended_plan = current_plan
    reason = f"Estimated usage fits within the {current_plan.display_name} plan."
    if current_plan.token_quota != -1 and total_tokens > current_plan.token_quota:
        eligible = session.exec(
            select(Plan)
            .where((Plan.token_quota == -1) | (Plan.token_quota >= total_tokens))
            .order_by(Plan.monthly_price_cents)
        ).all()
        if eligible:
            recommended_plan = eligible[0]
            multiple = total_tokens / current_plan.token_quota
            reason = f"Estimated token usage exceeds {current_plan.display_name} tier quota by {multiple:.0f}x"

    return {
        "model": model.slug,
        "period_days": payload.days,
        "estimated_requests": estimated_requests,
        "estimated_tokens": {
            "input": total_input, "cached_input": total_cached,
            "output": total_output, "reasoning": total_reasoning,
        },
        "cost_breakdown": {
            "input_cost": _fmt_dollars(input_cost),
            "cached_input_cost": _fmt_dollars(cached_cost),
            "output_cost": _fmt_dollars(output_cost),
            "reasoning_cost": _fmt_dollars(reasoning_cost),
            "total": _fmt_dollars(total_cost),
        },
        "plan_recommendation": {
            "current_plan": current_plan.name,
            "recommended_plan": recommended_plan.name,
            "reason": reason,
        },
    }