from fastapi import APIRouter, Request, Response, status

from app.core.config import get_settings
from app.core.security import CurrentUser, session_token
from app.db.session import DB
from app.schemas.auth import LoginRequest, UserOut
from app.schemas.common import UNAUTHORIZED, VALIDATION, ErrorResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,  # unreadable from JavaScript
        secure=settings.cookie_secure,
        samesite="lax",  # not sent on cross-site POST/PATCH/DELETE -> CSRF protection
        path="/",
    )


@router.post(
    "/login",
    response_model=UserOut,
    summary="Sign in",
    description="Verifies credentials and sets an HttpOnly session cookie.",
    responses={
        **UNAUTHORIZED,
        **VALIDATION,
        429: {"model": ErrorResponse, "description": "Too many failed attempts."},
    },
)
def login(body: LoginRequest, response: Response, db: DB) -> UserOut:
    user, token = auth_service.login(db, body.email, body.password)
    _set_session_cookie(response, token)
    return UserOut.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out",
    description="Revokes the current session and clears the cookie. Safe to call when signed out.",
)
def logout(request: Request, response: Response, db: DB) -> None:
    auth_service.logout(db, session_token(request))
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.get("/me", response_model=UserOut, summary="Current user", responses=UNAUTHORIZED)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
