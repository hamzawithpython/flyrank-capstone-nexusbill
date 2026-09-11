from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from uuid import UUID
from app.core.deps import get_owned_project
from app.core.api_keys import generate_api_key
from app.db import get_session
from app.models import Project, ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = APIRouter(prefix="/projects/{project_id}/keys", tags=["api_keys"])


@router.post("", response_model=ApiKeyCreated)
def create_key(
    payload: ApiKeyCreate,
    project: Project = Depends(get_owned_project),
    session: Session = Depends(get_session),
):
    full_key, key_prefix, key_hash = generate_api_key()
    key = ApiKey(project_id=project.id, key_hash=key_hash, key_prefix=key_prefix, name=payload.name)
    session.add(key)
    session.commit()
    session.refresh(key)
    return ApiKeyCreated(id=key.id, name=key.name, key=full_key, key_prefix=key_prefix)


@router.get("", response_model=list[ApiKeyRead])
def list_keys(
    project: Project = Depends(get_owned_project),
    session: Session = Depends(get_session),
):
    return session.exec(select(ApiKey).where(ApiKey.project_id == project.id)).all()


@router.delete("/{key_id}", response_model=ApiKeyRead)
def revoke_key(
    key_id: UUID,
    project: Project = Depends(get_owned_project),
    session: Session = Depends(get_session),
):
    key = session.get(ApiKey, key_id)
    if key is None or key.project_id != project.id:
        raise HTTPException(status_code=404, detail="API key not found")
    key.status = "revoked"
    key.revoked_at = datetime.utcnow()
    session.add(key)
    session.commit()
    session.refresh(key)
    return key