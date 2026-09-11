from fastapi import APIRouter, Depends
from app.core.deps import get_caller_org
from app.models import Organization

router = APIRouter(prefix="/org", tags=["organizations"])

@router.get("")
def get_my_org(org: Organization = Depends(get_caller_org)):
    return org