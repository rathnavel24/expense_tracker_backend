import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthSession


def add(db: Session, *, user_id: uuid.UUID, token_hash: bytes, expires_at: datetime) -> AuthSession:
    session = AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(session)
    db.flush()
    return session


def get_active(db: Session, token_hash: bytes, now: datetime) -> AuthSession | None:
    return db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash, AuthSession.expires_at > now
        )
    )


def delete_by_token_hash(db: Session, token_hash: bytes) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))


def delete_expired(db: Session, user_id: uuid.UUID, now: datetime) -> None:
    db.execute(
        delete(AuthSession).where(AuthSession.user_id == user_id, AuthSession.expires_at <= now)
    )


def delete_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
