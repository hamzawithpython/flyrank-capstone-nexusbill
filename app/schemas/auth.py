from pydantic import BaseModel, EmailStr
from uuid import UUID

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    org_name: str

class RegisterResponse(BaseModel):
    access_token: str
    org_id: UUID