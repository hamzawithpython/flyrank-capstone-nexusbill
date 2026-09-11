from fastapi import APIRouter, Depends
from app.core.api_auth import get_api_key_context, ApiKeyContext

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