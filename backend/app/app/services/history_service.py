from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import TransactionType, User
from app.schemas.history import MonthlyHistory
from app.services import stats_service as stats
from app.services.transaction_service import fetch_transactions
from app.utils import month_range

ZERO = Decimal("0.00")
# A month of personal transactions is small; this is a safety cap, not a page size.
MAX_PER_MONTH = 2000


def monthly(
    db: Session, user: User, year: int, month: int, type_: TransactionType | None
) -> MonthlyHistory:
    start, end = month_range(year, month)
    totals = stats.totals_by_type(db, user.id, start, end)
    by_day = stats.expense_totals_by_day(db, user.id, start, end)
    items = fetch_transactions(db, user.id, limit=MAX_PER_MONTH, type_=type_, start=start, end=end)

    days: list[dict[str, object]] = []
    for t in items:  # already newest first
        if not days or days[-1]["date"] != t.occurred_on:
            days.append(
                {
                    "date": t.occurred_on,
                    "total_expenses": by_day.get(t.occurred_on, ZERO),
                    "transactions": [],
                }
            )
        day_items = days[-1]["transactions"]
        assert isinstance(day_items, list)
        day_items.append(t)

    income = totals.get(TransactionType.INCOME)
    expenses = totals.get(TransactionType.EXPENSE)
    return MonthlyHistory.model_validate(
        {
            "year": year,
            "month": month,
            "entry_count": (income.count if income else 0) + (expenses.count if expenses else 0),
            "total_expenses": expenses.amount if expenses else ZERO,
            "total_income": income.amount if income else ZERO,
            "days": days,
        }
    )
