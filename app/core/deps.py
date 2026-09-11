from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from uuid import UUID
from app.core.security import get_current_user
from app.db import get_session
from app.models import Organization, Project

def get_caller_org(
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Organization:
    org = session.exec(
        select(Organization).where(Organization.owner_user_id == user["sub"])
    ).first()
    if org is None:
        raise HTTPException(status_code=404, detail="No organization found for this user")
    return org


def get_owned_project(
    project_id: UUID,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.org_id != org.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project