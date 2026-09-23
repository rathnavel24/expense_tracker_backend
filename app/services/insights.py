from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models import TransactionType, User
from app.repositories import transactions
from app.schemas.insights import MonthlyInsights
from app.services.months import month_range, shift_month

TREND_MONTHS = 6
ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def monthly(db: Session, user: User, year: int, month: int, today: date) -> MonthlyInsights:
    start, end = month_range(year, month)
    by_day = transactions.expense_totals_by_day(db, user.id, start, end)
    days = [start + timedelta(n) for n in range((end - start).days)]
    daily = [{"date": d, "amount": by_day.get(d, ZERO)} for d in days]

    elapsed = [d for d in days if d <= today]
    elapsed_total = sum((by_day.get(d, ZERO) for d in elapsed), ZERO)
    average = (elapsed_total / len(elapsed)).quantize(CENT, ROUND_HALF_UP) if elapsed else None
    highest = max(by_day.items(), key=lambda kv: (kv[1], kv[0]), default=None)

    trend_start = month_range(*shift_month(year, month, -(TREND_MONTHS - 1)))[0]
    by_month = transactions.totals_by_month(db, user.id, trend_start, end)
    trend = []
    for offset in range(TREND_MONTHS - 1, -1, -1):
        y, m = shift_month(year, month, -offset)
        trend.append(
            {
                "year": y,
                "month": m,
                "total_expenses": by_month.get((y, m, TransactionType.EXPENSE), ZERO),
                "total_income": by_month.get((y, m, TransactionType.INCOME), ZERO),
            }
        )

    return MonthlyInsights.model_validate(
        {
            "year": year,
            "month": month,
            "total_expenses": sum(by_day.values(), ZERO),
            "daily": daily,
            "days_elapsed": len(elapsed),
            "average_daily": average,
            "highest_day": {"date": highest[0], "amount": highest[1]} if highest else None,
            "no_spend_days": sum(1 for d in elapsed if d not in by_day),
            "payment_methods": [
                {"method": method, "amount": amount, "count": count}
                for method, amount, count in transactions.expense_totals_by_payment_method(
                    db, user.id, start, end
                )
            ],
            "trend": trend,
        }
    )
