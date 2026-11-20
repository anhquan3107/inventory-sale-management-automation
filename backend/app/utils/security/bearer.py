
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from utils.security.jwt import decode_token
from sqlalchemy.orm import Session
from database.dependencies import get_db
from models.user import User

security = HTTPBearer(auto_error=True)


def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def require_admin(current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    try:
        user = db.get(User, int(current_user["sub"]))
    except (ValueError, KeyError):
        user = None
    if not user or not user.is_active or user.role != "admin" or current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Active administrator required")
    return current_user
