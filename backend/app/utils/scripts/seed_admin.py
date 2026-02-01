from pathlib import Path
import sys
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.context import CryptContext

from database.session import SessionLocal
from models import User




# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def seed_admin_user():
    db: Session = SessionLocal()

    try:
        admin_username = "admin"
        admin_password = "admin123"  # CHANGE AFTER FIRST LOGIN
        admin_role = "admin"

        # Check if admin already exists
        stmt = select(User).where(User.username == admin_username)
        existing_admin = db.execute(stmt).scalars().first()

        if existing_admin:
            print("Admin user already exists. No action taken.")
            return

        # Create admin user
        admin_user = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role=admin_role,
            is_active=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("Admin user created successfully.")
        print(f"Username: {admin_username}")
        print("Password: admin123 (please change after login)")

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()
