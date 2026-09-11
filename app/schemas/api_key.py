from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ApiKeyCreate(BaseModel):
    name: str

class ApiKeyCreated(BaseModel):
    id: UUID
    name: str
    key: str          # full plaintext key — present ONLY in this response
    key_prefix: str

class ApiKeyRead(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime
    revoked_at: Optional[datetime]