from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: Optional[UUID] = Field(default=None, foreign_key="organizations.id")
    actor: str
    event_type: str
    payload: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)