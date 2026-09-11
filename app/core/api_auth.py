import hashlib
from datetime import datetime
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from app.db import get_session
from app.models import ApiKey, Project, Organization

api_key_security = HTTPBearer()


class ApiKeyContext:
    def __init__(self, api_key: ApiKey, project: Project, org: Organization):
        self.api_key = api_key
        self.project = project
        self.org = org


def get_api_key_context(
    credentials: HTTPAuthorizationCredentials = Depends(api_key_security),
    session: Session = Depends(get_session),
) -> ApiKeyContext:
    raw_key = credentials.credentials
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = session.exec(select(ApiKey).where(ApiKey.key_hash == key_hash)).first()
    if api_key is None or api_key.status != "active":
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    project = session.get(Project, api_key.project_id)
    org = session.get(Organization, project.org_id)

    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)
    session.commit()

    return ApiKeyContext(api_key=api_key, project=project, org=org)