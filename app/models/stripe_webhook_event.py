from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class StripeWebhookEvent(SQLModel, table=True):
    __tablename__ = "stripe_webhook_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    stripe_event_id: str = Field(unique=True)
    event_type: str
    payload: dict = Field(sa_column=Column(JSONB))
    status: str = Field(default="pending")
    attempts: int = Field(default=0)
    last_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)