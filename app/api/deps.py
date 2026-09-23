from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.services import auth

DB = Annotated[Session, Depends(get_db)]


def session_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().session_cookie_name)


def current_user(db: DB, request: Request) -> User:
    """The authenticated user, derived solely from the session cookie - never from input."""
    return auth.authenticate(db, session_token(request))


CurrentUser = Annotated[User, Depends(current_user)]
