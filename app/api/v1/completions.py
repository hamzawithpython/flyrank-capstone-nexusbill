import time
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from app.core.api_auth import get_api_key_context, ApiKeyContext
from app.core.billing.calculator import calculate_cost_micros
from app.core.billing.quota import check_quota
from app.core.billing.metering import generate_mock_completion
from app.core.jobs.alerts import send_quota_alert
from fastapi import HTTPException
from app.db import get_session
from app.models import AIModel, UsageEvent, AuditLog
from app.schemas.completion import ChatCompletionRequest, ChatCompletionResponse, Usage

router = APIRouter(prefix="/v1", tags=["v1"])


@router.get("/whoami")
def whoami(ctx: ApiKeyContext = Depends(get_api_key_context)):
    return {
        "api_key_id": ctx.api_key.id,
        "api_key_name": ctx.api_key.name,
        "project_id": ctx.project.id,
        "project_name": ctx.project.name,
        "org_id": ctx.org.id,
        "org_name": ctx.org.name,
    }


@router.post("/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(
    payload: ChatCompletionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    ctx: ApiKeyContext = Depends(get_api_key_context),
    session: Session = Depends(get_session),
):
    start = time.monotonic()

    if ctx.org.status != "active":
        raise HTTPException(status_code=403, detail=f"Organization status is '{ctx.org.status}'")

    existing = session.exec(
        select(UsageEvent).where(UsageEvent.idempotency_key == idempotency_key)
    ).first()
    if existing is not None:
        return ChatCompletionResponse(
            id=str(existing.id),
            model=payload.model,
            content="(replayed — billing data shown is authoritative, original text not stored)",
            usage=Usage(
                input_tokens=existing.input_tokens,
                cached_input_tokens=existing.cached_input_tokens,
                output_tokens=existing.output_tokens,
                reasoning_tokens=existing.reasoning_tokens,
                total_cost_micros=existing.total_cost_micros,
            ),
            idempotent_replay=True,
        )

    model = session.exec(
        select(AIModel).where(AIModel.slug == payload.model, AIModel.is_active == True)
    ).first()
    if model is None:
        raise HTTPException(status_code=400, detail=f"Unknown or inactive model: {payload.model}")

    mock = generate_mock_completion([m.model_dump() for m in payload.messages])
    this_request_tokens = (
        mock["input_tokens"] + mock["cached_input_tokens"] + mock["output_tokens"] + mock["reasoning_tokens"]
    )

    # ONE quota check, BEFORE the event exists in the database — its return
    # value is the true pre-request usage, which the 80% transition check
    # below depends on being accurate.
    try:
        pre_call_count, pre_token_count = check_quota(
            org=ctx.org, plan=ctx.plan, this_request_tokens=this_request_tokens, session=session
        )
    except HTTPException as e:
        if e.status_code == 429:
            usage_type = e.detail.get("usage_type", "tokens")
            send_quota_alert.delay(str(ctx.org.id), "quota_100", usage_type)
        raise

    cost_micros = calculate_cost_micros(
        input_tokens=mock["input_tokens"],
        cached_input_tokens=mock["cached_input_tokens"],
        output_tokens=mock["output_tokens"],
        reasoning_tokens=mock["reasoning_tokens"],
        input_price_per_1m_micros=model.input_price_per_1m_micros,
        cached_input_price_per_1m_micros=model.cached_input_price_per_1m_micros,
        output_price_per_1m_micros=model.output_price_per_1m_micros,
        reasoning_price_per_1m_micros=model.reasoning_price_per_1m_micros,
    )

    duration_ms = int((time.monotonic() - start) * 1000)

    usage_event = UsageEvent(
        org_id=ctx.org.id,
        project_id=ctx.project.id,
        api_key_id=ctx.api_key.id,
        model_id=model.id,
        idempotency_key=idempotency_key,
        input_tokens=mock["input_tokens"],
        cached_input_tokens=mock["cached_input_tokens"],
        output_tokens=mock["output_tokens"],
        reasoning_tokens=mock["reasoning_tokens"],
        total_cost_micros=cost_micros,
        request_duration_ms=duration_ms,
        endpoint="/v1/chat/completions",
    )
    session.add(usage_event)

    session.add(AuditLog(
        org_id=ctx.org.id,
        actor=f"api_key:{ctx.api_key.id}",
        event_type="chat_completion",
        payload={"model": payload.model, "idempotency_key": idempotency_key, "cost_micros": cost_micros},
    ))

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise HTTPException(status_code=409, detail="Duplicate request detected during commit")

    session.refresh(usage_event)

    # 80% warning — uses pre_call_count/pre_token_count captured BEFORE
    # this event was inserted, so the transition math reflects reality,
    # not a self-referential comparison against data that now includes
    # this same request.
    if ctx.plan.token_quota != -1:
        pre_pct = pre_token_count / ctx.plan.token_quota
        post_pct = (pre_token_count + this_request_tokens) / ctx.plan.token_quota
        if pre_pct < 0.8 <= post_pct:
            send_quota_alert.delay(str(ctx.org.id), "quota_80", "tokens")
    if ctx.plan.api_call_quota != -1:
        pre_pct = pre_call_count / ctx.plan.api_call_quota
        post_pct = (pre_call_count + 1) / ctx.plan.api_call_quota
        if pre_pct < 0.8 <= post_pct:
            send_quota_alert.delay(str(ctx.org.id), "quota_80", "api_calls")

    return ChatCompletionResponse(
        id=str(usage_event.id),
        model=payload.model,
        content=mock["content"],
        usage=Usage(
            input_tokens=usage_event.input_tokens,
            cached_input_tokens=usage_event.cached_input_tokens,
            output_tokens=usage_event.output_tokens,
            reasoning_tokens=usage_event.reasoning_tokens,
            total_cost_micros=usage_event.total_cost_micros,
        ),
        idempotent_replay=False,
    )