from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.security import get_current_user
from app.db import get_session
from app.models import Organization

router = APIRouter(prefix="/org", tags=["organizations"])

@router.get("")
def get_my_org(
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    org = session.exec(
        select(Organization).where(Organization.owner_user_id == user["sub"])
    ).first()

    if org is None:
        raise HTTPException(status_code=404, detail="No organization found for this user")

    return org