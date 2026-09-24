import threading
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidCredentialsError, TooManyAttemptsError
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    password_needs_rehash,
    verify_password,
)
from app.models import AuthSession, User

settings = get_settings()


class LoginThrottle:
    """In-process throttle for failed logins, keyed by email.

    Deliberately simple: the app runs as a single process for a single user. With several
    workers each keeps its own counters (still a useful brake).
    """

    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and now - attempts[0] > self._window:
            attempts.popleft()
        return attempts

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self._max

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


_throttle = LoginThrottle(settings.login_max_failures, settings.login_failure_window_minutes * 60)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def _delete_sessions(db: Session, *conditions: ColumnElement[bool]) -> None:
    db.execute(delete(AuthSession).where(*conditions))


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    """Verify credentials and open a session. Returns the user and the raw session token."""
    key = email.strip().lower()
    if _throttle.is_blocked(key):
        raise TooManyAttemptsError("Too many failed attempts. Please wait a few minutes.")

    user = get_user_by_email(db, key)
    if not verify_password(user.password_hash if user else None, password) or user is None:
        _throttle.record_failure(key)
        raise InvalidCredentialsError("Incorrect email or password.")
    _throttle.reset(key)

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    now = datetime.now(UTC)
    _delete_sessions(db, AuthSession.user_id == user.id, AuthSession.expires_at <= now)
    token = new_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=now + timedelta(days=settings.session_ttl_days),
        )
    )
    db.commit()
    return user, token


def logout(db: Session, token: str | None) -> None:
    if token:
        _delete_sessions(db, AuthSession.token_hash == hash_session_token(token))
        db.commit()


def create_user(db: Session, *, email: str, name: str, password: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise ValueError(f"A user with email {email!r} already exists.")
    user = User(
        email=email.strip().lower(), name=name.strip(), password_hash=hash_password(password)
    )
    db.add(user)
    db.commit()
    return user


def set_password(db: Session, *, email: str, password: str) -> None:
    user = get_user_by_email(db, email)
    if user is None:
        raise ValueError(f"No user with email {email!r}.")
    user.password_hash = hash_password(password)
    # Changing the password signs out every existing session.
    _delete_sessions(db, AuthSession.user_id == user.id)
    db.commit()
