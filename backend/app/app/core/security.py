import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, Request
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import NotAuthenticatedError
from app.db.session import DB
from app.models import AuthSession, User
from app.services.recurring_service import generate_due

_hasher = PasswordHasher()  # Argon2id with library-recommended parameters

# Verified against when the email is unknown, so response time does not reveal
# whether an account exists.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

# Refresh `last_seen_at`/`expires_at` at most this often, to avoid a write on every request.
_TOUCH_INTERVAL = timedelta(hours=1)


# --- Passwords ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-work check: an unknown user (`password_hash=None`) still costs one hash."""
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerificationError, InvalidHashError):
        return False
    return password_hash is not None


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# --- Session tokens ------------------------------------------------------------------------


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def session_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().session_cookie_name)


# --- Dependencies --------------------------------------------------------------------------


def get_current_user(db: DB, request: Request) -> User:
    """The authenticated user, derived solely from the session cookie - never from input.
    Sliding expiry: an active session is extended as it's used."""
    token = session_token(request)
    if not token:
        raise NotAuthenticatedError("Please sign in.")
    now = datetime.now(UTC)
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == hash_session_token(token), AuthSession.expires_at > now
        )
    )
    if session is None:
        raise NotAuthenticatedError("Your session has expired. Please sign in again.")

    if now - session.last_seen_at > _TOUCH_INTERVAL:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=get_settings().session_ttl_days)
        db.commit()
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_synced_user(db: DB, user: CurrentUser) -> User:
    """The current user, after generating any recurring transactions that are now due.
    Use on every route that reads transaction data, so totals are never stale."""
    generate_due(db, user)
    return user


SyncedUser = Annotated[User, Depends(get_synced_user)]
