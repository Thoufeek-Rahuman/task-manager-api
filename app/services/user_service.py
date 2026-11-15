from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email.lower())).scalars().first()


def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        email=user.email.lower(), hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    return db_user
