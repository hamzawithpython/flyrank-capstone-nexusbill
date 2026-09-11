from sqlmodel import SQLModel, Field
from datetime import date, datetime
from uuid import UUID, uuid4

class UsageRollup(SQLModel, table=True):
    __tablename__ = "usage_rollups"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="organizations.id")
    period_start: date
    period_end: date
    api_calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_cost_micros: int = 0
    computed_at: datetime = Field(default_factory=datetime.utcnow)