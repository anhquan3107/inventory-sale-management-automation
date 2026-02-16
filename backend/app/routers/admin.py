from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from schemas.admin import AdminResetPasswordRequest
from services.admin import admin_reset_password
from utils.security.bearer import require_auth


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.put(
    "/users/{user_id}/reset-password"
)
def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    try:
        admin_reset_password(
            db,
            user_id,
            payload.new_password
        )
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
