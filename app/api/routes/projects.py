from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime
from uuid import UUID
from app.core.deps import get_caller_org
from app.db import get_session
from app.models import Organization, Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_owned_project(project_id: UUID, org_id: UUID, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None or project.org_id != org_id:
        # Same 404 whether the project doesn't exist at all, or exists but
        # belongs to a different org. Returning 403 for the second case would
        # leak that the ID is valid — a small but real cross-tenant information
        # leak. A 404 tells an attacker nothing either way.
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=ProjectRead)
def create_project(
    payload: ProjectCreate,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    project = Project(org_id=org.id, name=payload.name, description=payload.description)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    include_archived: bool = False,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    query = select(Project).where(Project.org_id == org.id)
    if not include_archived:
        query = query.where(Project.archived_at == None)
    return session.exec(query).all()


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    return _get_owned_project(project_id, org.id, session)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    project = _get_owned_project(project_id, org.id, session)
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}", response_model=ProjectRead)
def archive_project(
    project_id: UUID,
    org: Organization = Depends(get_caller_org),
    session: Session = Depends(get_session),
):
    project = _get_owned_project(project_id, org.id, session)
    project.archived_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project