from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    plan: str  # "pro" or "enterprise"