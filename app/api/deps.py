from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.services import auth, recurring

DB = Annotated[Session, Depends(get_db)]


def session_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().session_cookie_name)


def current_user(db: DB, request: Request) -> User:
    """The authenticated user, derived solely from the session cookie - never from input."""
    return auth.authenticate(db, session_token(request))


CurrentUser = Annotated[User, Depends(current_user)]


def synced_user(db: DB, user: CurrentUser) -> User:
    """The current user, after generating any recurring transactions that are now due.
    Use on every route that reads transaction data, so totals are never stale."""
    recurring.generate_due(db, user)
    return user


SyncedUser = Annotated[User, Depends(synced_user)]
