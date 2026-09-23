from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidCredentialsError, NotAuthenticatedError, TooManyAttemptsError
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    password_needs_rehash,
    verify_password,
)
from app.models import User
from app.repositories import auth_sessions, users
from app.services.login_throttle import LoginThrottle

settings = get_settings()
_throttle = LoginThrottle(settings.login_max_failures, settings.login_failure_window_minutes * 60)

# Refresh `last_seen_at`/`expires_at` at most this often, to avoid a write on every request.
_TOUCH_INTERVAL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(UTC)


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    """Verify credentials and open a session. Returns the user and the raw session token."""
    key = email.strip().lower()
    if _throttle.is_blocked(key):
        raise TooManyAttemptsError("Too many failed attempts. Please wait a few minutes.")

    user = users.get_by_email(db, key)
    if not verify_password(user.password_hash if user else None, password) or user is None:
        _throttle.record_failure(key)
        raise InvalidCredentialsError("Incorrect email or password.")
    _throttle.reset(key)

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    now = _now()
    auth_sessions.delete_expired(db, user.id, now)
    token = new_session_token()
    auth_sessions.add(
        db,
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=now + timedelta(days=settings.session_ttl_days),
    )
    db.commit()
    return user, token


def authenticate(db: Session, token: str | None) -> User:
    """Resolve a session token to its user, sliding the expiry forward on activity."""
    if not token:
        raise NotAuthenticatedError("Please sign in.")
    now = _now()
    session = auth_sessions.get_active(db, hash_session_token(token), now)
    if session is None:
        raise NotAuthenticatedError("Your session has expired. Please sign in again.")

    if now - session.last_seen_at > _TOUCH_INTERVAL:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=settings.session_ttl_days)
        db.commit()
    return session.user


def logout(db: Session, token: str | None) -> None:
    if token:
        auth_sessions.delete_by_token_hash(db, hash_session_token(token))
        db.commit()


def create_user(db: Session, *, email: str, name: str, password: str) -> User:
    if users.get_by_email(db, email) is not None:
        raise ValueError(f"A user with email {email!r} already exists.")
    user = users.add(db, email=email, name=name, password_hash=hash_password(password))
    db.commit()
    return user


def set_password(db: Session, *, email: str, password: str) -> None:
    user = users.get_by_email(db, email)
    if user is None:
        raise ValueError(f"No user with email {email!r}.")
    user.password_hash = hash_password(password)
    # Changing the password signs out every existing session.
    auth_sessions.delete_all_for_user(db, user.id)
    db.commit()
