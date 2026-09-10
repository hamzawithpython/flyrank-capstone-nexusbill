from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"user_id": user["sub"], "email": user.get("email")}