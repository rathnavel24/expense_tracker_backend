from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import TransactionType, User
from app.repositories import transactions
from app.schemas.dashboard import MonthlyDashboard
from app.services.months import month_range

RECENT_LIMIT = 8
_ZERO = Decimal("0.00")


def monthly(db: Session, user: User, year: int, month: int) -> MonthlyDashboard:
    """All numbers are computed in Postgres with exact NUMERIC arithmetic."""
    start, end = month_range(year, month)
    totals = transactions.totals_by_type(db, user.id, start, end)
    income = totals.get(TransactionType.INCOME)
    expenses = totals.get(TransactionType.EXPENSE)

    breakdown = transactions.expense_totals_by_category(db, user.id, start, end)
    recent = transactions.list_page(db, user.id, limit=RECENT_LIMIT, start=start, end=end)

    return MonthlyDashboard.model_validate(
        {
            "year": year,
            "month": month,
            "total_income": income.amount if income else _ZERO,
            "total_expenses": expenses.amount if expenses else _ZERO,
            "income_count": income.count if income else 0,
            "expense_count": expenses.count if expenses else 0,
            "expense_breakdown": [
                {"category": category, "amount": amount, "count": count}
                for category, amount, count in breakdown
            ],
            "recent_transactions": recent,
        }
    )
