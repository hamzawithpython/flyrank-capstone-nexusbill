from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id")
    key_hash: str = Field(unique=True)
    key_prefix: str
    name: str
    status: str = Field(default="active")
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None