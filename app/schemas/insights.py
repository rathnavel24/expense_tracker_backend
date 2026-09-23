from datetime import date

from pydantic import BaseModel, Field

from app.models.transaction import PaymentMethod
from app.schemas.common import Money


class DayTotal(BaseModel):
    date: date
    amount: Money


class PaymentMethodTotal(BaseModel):
    method: PaymentMethod | None = Field(description="null = not recorded")
    amount: Money
    count: int


class MonthTotal(BaseModel):
    year: int
    month: int
    total_expenses: Money
    total_income: Money


class MonthlyInsights(BaseModel):
    year: int
    month: int
    total_expenses: Money
    daily: list[DayTotal] = Field(
        description="Expenses for every day of the month (zeros included)."
    )
    days_elapsed: int = Field(
        description="Days of the month up to `today` (all days for past months, 0 for future)."
    )
    average_daily: Money | None = Field(
        description="Spending in elapsed days / days elapsed; null if no day has elapsed."
    )
    highest_day: DayTotal | None
    no_spend_days: int = Field(description="Elapsed days with no expenses.")
    payment_methods: list[PaymentMethodTotal]
    trend: list[MonthTotal] = Field(description="Six months ending with this one, oldest first.")
