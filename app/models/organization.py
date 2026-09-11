from sqlmodel import SQLModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: UUID = Field(unique=True, index=True)
    name: str
    email: str
    stripe_customer_id: Optional[str] = None
    plan_id: Optional[UUID] = Field(default=None, foreign_key="plans.id")
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)