from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

class ReconciliationReport(SQLModel, table=True):
    __tablename__ = "reconciliation_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_at: datetime = Field(default_factory=datetime.utcnow)
    orgs_checked: int
    mismatches: Optional[list] = Field(default=None, sa_column=Column(JSONB))
    status: str