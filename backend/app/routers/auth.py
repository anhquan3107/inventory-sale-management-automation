from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserMeResponse
)
from services.auth_service import (
    authenticate_user,
    get_user_by_id
)
from utils.security.bearer import require_auth

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    try:
        return authenticate_user(
            db,
            payload.username,
            payload.password
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )


@router.get(
    "/me",
    response_model=UserMeResponse
)
def get_me(
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    user_id = int(current_user["sub"])

    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role
    }
