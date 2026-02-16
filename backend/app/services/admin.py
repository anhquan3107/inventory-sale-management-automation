from sqlalchemy.orm import Session

from models import User
from services.auth import get_user_by_id, pwd_context


def admin_reset_password(
    db: Session,
    user_id: int,
    new_password: str
) -> None:
    user = get_user_by_id(db, user_id)

    if not user:
        raise ValueError("User not found")

    user.password_hash = pwd_context.hash(new_password)
    user.must_change_password = True

    db.commit()
