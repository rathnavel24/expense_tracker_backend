from datetime import date

from pydantic import BaseModel, Field

from app.schemas.category import CategoryOut
from app.schemas.common import Money
from app.schemas.transaction import TransactionOut


class CategoryTotal(BaseModel):
    category: CategoryOut
    amount: Money
    count: int
    previous_amount: Money = Field(
        description="Spent in this category during the comparison period (see `comparison`)."
    )


class TodaySummary(BaseModel):
    date: date
    total_expenses: Money
    expense_count: int
    total_income: Money


class Comparison(BaseModel):
    """The period this month is compared against.

    For the month containing `today`, that's the previous month *up to the same day*
    (1-24 Sep vs 1-24 Aug), so a half-finished month isn't compared to a whole one.
    Otherwise it's the whole previous month.
    """

    year: int
    month: int
    through_day: int | None = Field(description="Last day included; null = whole month.")
    total_expenses: Money
    total_income: Money


class MonthlyDashboard(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    total_income: Money
    total_expenses: Money
    income_count: int
    expense_count: int
    today: TodaySummary | None = Field(
        description="Present when the requested `today` falls in this month."
    )
    comparison: Comparison
    expense_breakdown: list[CategoryTotal] = Field(
        description="Expense totals per category for the month, largest first."
    )
    recent_transactions: list[TransactionOut] = Field(
        description="Most recent transactions in the month, newest first."
    )
