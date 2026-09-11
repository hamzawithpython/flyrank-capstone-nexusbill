from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectRead(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    archived_at: Optional[datetime]