from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import TransactionType, User
from app.repositories import transactions
from app.schemas.dashboard import MonthlyDashboard
from app.services.months import month_range, shift_month
from app.services.recurrence import occurrence_in

RECENT_LIMIT = 8
ZERO = Decimal("0.00")


def monthly(db: Session, user: User, year: int, month: int, today: date | None) -> MonthlyDashboard:
    """All numbers are computed in Postgres with exact NUMERIC arithmetic.

    `today` is the viewer's calendar date (sent by the device), used for the Today card and
    for a like-for-like comparison with the previous month.
    """
    start, end = month_range(year, month)
    in_month = today is not None and start <= today < end

    totals = transactions.totals_by_type(db, user.id, start, end)
    income = totals.get(TransactionType.INCOME)
    expenses = totals.get(TransactionType.EXPENSE)

    # Comparison period: previous month, cut at the same day when viewing the current month.
    prev_year, prev_month = shift_month(year, month, -1)
    prev_start, prev_end = month_range(prev_year, prev_month)
    through_day = None
    if in_month:
        assert today is not None
        through_day = today.day
        prev_end = min(prev_end, occurrence_in(prev_year, prev_month, today.day) + timedelta(1))
    prev_totals = transactions.totals_by_type(db, user.id, prev_start, prev_end)
    prev_by_category = {
        category.id: amount
        for category, amount, _ in transactions.expense_totals_by_category(
            db, user.id, prev_start, prev_end
        )
    }

    today_summary = None
    if in_month:
        assert today is not None
        day = transactions.totals_by_type(db, user.id, today, today + timedelta(1))
        day_exp = day.get(TransactionType.EXPENSE)
        day_inc = day.get(TransactionType.INCOME)
        today_summary = {
            "date": today,
            "total_expenses": day_exp.amount if day_exp else ZERO,
            "expense_count": day_exp.count if day_exp else 0,
            "total_income": day_inc.amount if day_inc else ZERO,
        }

    breakdown = transactions.expense_totals_by_category(db, user.id, start, end)
    recent = transactions.list_page(db, user.id, limit=RECENT_LIMIT, start=start, end=end)

    def amount_of(t: transactions.TypeTotal | None) -> Decimal:
        return t.amount if t else ZERO

    return MonthlyDashboard.model_validate(
        {
            "year": year,
            "month": month,
            "total_income": amount_of(income),
            "total_expenses": amount_of(expenses),
            "income_count": income.count if income else 0,
            "expense_count": expenses.count if expenses else 0,
            "today": today_summary,
            "comparison": {
                "year": prev_year,
                "month": prev_month,
                "through_day": through_day,
                "total_expenses": amount_of(prev_totals.get(TransactionType.EXPENSE)),
                "total_income": amount_of(prev_totals.get(TransactionType.INCOME)),
            },
            "expense_breakdown": [
                {
                    "category": category,
                    "amount": amount,
                    "count": count,
                    "previous_amount": prev_by_category.get(category.id, ZERO),
                }
                for category, amount, count in breakdown
            ],
            "recent_transactions": recent,
        }
    )
