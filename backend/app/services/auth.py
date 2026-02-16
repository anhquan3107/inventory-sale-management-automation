from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.context import CryptContext

from models import User
from utils.security.jwt import (
    create_access_token,
    create_refresh_token
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False
)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def authenticate_user(
    db: Session,
    identifier: str,
    password: str
) -> dict:
    stmt = select(User).where(
        (User.username == identifier) |
        (User.email == identifier),
        User.is_active == True
    )
    user = db.execute(stmt).scalars().first()

    if not user:
        raise ValueError("Invalid credentials")

    if not verify_password(
        password,
        user.password_hash
    ):
        raise ValueError("Invalid credentials")

    payload = {
        "sub": str(user.id),
        "role": user.role
    }

    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "must_change_password": user.must_change_password
    }



def get_user_by_id(
    db: Session,
    user_id: int
) -> User | None:
    stmt = select(User).where(User.id == user_id)
    return db.execute(stmt).scalars().first()

def change_password(
    db: Session,
    user_id: int,
    current_password: str,
    new_password: str
) -> None:
    user = get_user_by_id(db, user_id)

    if not user:
        raise ValueError("User not found")

    if not verify_password(
        current_password,
        user.password_hash
    ):
        raise ValueError("Incorrect password")

    user.password_hash = pwd_context.hash(new_password)
    user.must_change_password = False

    db.commit()
