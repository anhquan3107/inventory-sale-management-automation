from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserMeResponse,
    ChangePasswordRequest
)
from services.auth import (
    authenticate_user,
    change_password,
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
            payload.identifier,
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

@router.put(
    "/change-password"
)
def update_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    try:
        change_password(
            db,
            int(current_user["sub"]),
            payload.current_password,
            payload.new_password
        )
        return {"message": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
