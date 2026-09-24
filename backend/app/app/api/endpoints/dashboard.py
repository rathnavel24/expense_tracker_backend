from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import SyncedUser
from app.db.session import DB
from app.schemas.common import UNAUTHORIZED, VALIDATION
from app.schemas.dashboard import MonthlyDashboard
from app.services import dashboard_service
from app.utils import today as app_today

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/monthly",
    response_model=MonthlyDashboard,
    summary="Monthly summary",
    description="Everything the home screen needs for one month in a single request: "
    "income and expense totals, expense breakdown by category, and recent activity.",
    responses={**UNAUTHORIZED, **VALIDATION},
)
def monthly_dashboard(
    user: SyncedUser,
    db: DB,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    today: Annotated[
        date | None,
        Query(
            description="The viewer's local date; enables the Today card and like-for-like "
            "comparison. Defaults to today in the app timezone."
        ),
    ] = None,
) -> MonthlyDashboard:
    return dashboard_service.monthly(db, user, year, month, today or app_today())
