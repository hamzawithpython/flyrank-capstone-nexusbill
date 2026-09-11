from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from datetime import datetime
from app.core.deps import get_caller_org, get_owned_project
from app.db import get_session
from app.models import Organization, Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


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
def get_project(project: Project = Depends(get_owned_project)):
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_owned_project),
    session: Session = Depends(get_session),
):
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
    project: Project = Depends(get_owned_project),
    session: Session = Depends(get_session),
):
    project.archived_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project