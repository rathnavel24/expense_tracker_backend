from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import SyncedUser
from app.db.session import DB
from app.schemas.common import UNAUTHORIZED, VALIDATION
from app.schemas.insights import MonthlyInsights
from app.services import insights_service
from app.utils import today as app_today

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get(
    "/monthly",
    response_model=MonthlyInsights,
    summary="Monthly insights",
    description="Daily spending, averages, payment-method breakdown and a six-month trend "
    "for one month, in a single request.",
    responses={**UNAUTHORIZED, **VALIDATION},
)
def monthly_insights(
    user: SyncedUser,
    db: DB,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    today: Annotated[
        date | None,
        Query(description="The viewer's local date. Defaults to today in the app timezone."),
    ] = None,
) -> MonthlyInsights:
    return insights_service.monthly(db, user, year, month, today or app_today())
