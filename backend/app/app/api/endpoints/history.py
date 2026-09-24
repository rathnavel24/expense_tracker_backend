from typing import Annotated

from fastapi import APIRouter, Query

from app.core.security import SyncedUser
from app.db.session import DB
from app.models import TransactionType
from app.schemas.common import UNAUTHORIZED, VALIDATION
from app.schemas.history import MonthlyHistory
from app.services import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get(
    "/monthly",
    response_model=MonthlyHistory,
    summary="Month of transactions, grouped by day",
    description="Every transaction in the month grouped by date, with each day's expense "
    "total and the month's totals.",
    responses={**UNAUTHORIZED, **VALIDATION},
)
def monthly_history(
    user: SyncedUser,
    db: DB,
    year: Annotated[int, Query(ge=2000, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
    type: TransactionType | None = None,
) -> MonthlyHistory:
    return history_service.monthly(db, user, year, month, type)
