from sqlmodel import SQLModel, Field
from datetime import date, datetime
from uuid import UUID, uuid4

class UsageAlert(SQLModel, table=True):
    __tablename__ = "usage_alerts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(foreign_key="organizations.id")
    alert_type: str
    usage_type: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: date