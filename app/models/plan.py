from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True)
    display_name: str
    monthly_price_cents: int
    api_call_quota: int
    token_quota: int
    rate_limit_rpm: int