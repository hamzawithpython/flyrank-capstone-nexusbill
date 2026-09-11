import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.security import get_current_user
from app.db import get_session
from app.models import Organization
from app.schemas.auth import RegisterRequest, RegisterResponse

router = APIRouter(prefix="/auth", tags=["auth"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def _delete_supabase_user(user_id: str) -> None:
    httpx.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        },
    )


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": SUPABASE_KEY, "Content-Type": "application/json"},
        json={"email": payload.email, "password": payload.password},
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Supabase signup failed: {resp.text}")

    data = resp.json()
    user_id = data["user"]["id"]

    try:
        org = Organization(
            owner_user_id=user_id,
            name=payload.org_name,
            email=payload.email,
        )
        session.add(org)
        session.commit()
        session.refresh(org)
    except Exception as e:
        session.rollback()
        # The compensating action can fail too — never let that failure
        # hide the original error. Surface both, always.
        try:
            _delete_supabase_user(user_id)
            cleanup_note = "Supabase user was rolled back successfully."
        except Exception as cleanup_err:
            cleanup_note = f"Rollback ALSO failed — orphaned Supabase user {user_id}: {cleanup_err}"
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {e}. {cleanup_note}",
        )

    return RegisterResponse(access_token=data["access_token"], org_id=org.id)


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"user_id": user["sub"], "email": user.get("email")}