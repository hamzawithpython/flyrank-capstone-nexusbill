from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import date
from app.core.deps import get_caller_org
from app.db import get_session
from app.models import Organization, UsageRollup

router = APIRouter(prefix="/org/usage", tags=["usage"])


@router.get("")
def get_current_usage(
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    period_start = date.today().replace(day=1)
    rollup = session.exec(
        select(UsageRollup).where(
            UsageRollup.org_id == org.id,
            UsageRollup.period_start == period_start,
        )
    ).first()
    if rollup is None:
        raise HTTPException(
            status_code=404,
            detail="No usage rollup computed yet for the current period. The rollup job runs nightly at 01:00.",
        )
    return rollup