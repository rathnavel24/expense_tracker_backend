from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DB, CurrentUser
from app.api.responses import UNAUTHORIZED, VALIDATION
from app.schemas.dashboard import MonthlyDashboard
from app.services import dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/monthly",
    response_model=MonthlyDashboard,
    summary="Monthly summary",
    description="Everything the home screen needs for one month in a single request: "
    "income and expense totals, expense breakdown by category, and recent activity.",
    responses={**UNAUTHORIZED, **VALIDATION},
)
def monthly_dashboard(
    user: CurrentUser,
    db: DB,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> MonthlyDashboard:
    return dashboard.monthly(db, user, year, month)
