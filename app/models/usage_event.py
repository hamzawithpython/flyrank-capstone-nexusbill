from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class UsageEvent(SQLModel, table=True):
    __tablename__ = "usage_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="organizations.id")
    project_id: UUID = Field(foreign_key="projects.id")
    api_key_id: UUID = Field(foreign_key="api_keys.id")
    model_id: UUID = Field(foreign_key="models.id")
    idempotency_key: str = Field(unique=True)
    input_tokens: int
    cached_input_tokens: int = 0
    output_tokens: int
    reasoning_tokens: int = 0
    total_cost_micros: int
    request_duration_ms: Optional[int] = None
    endpoint: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)