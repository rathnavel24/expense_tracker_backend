import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def get(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def add(db: Session, *, email: str, name: str, password_hash: str) -> User:
    user = User(email=email.strip().lower(), name=name.strip(), password_hash=password_hash)
    db.add(user)
    db.flush()
    return user
