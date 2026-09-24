from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import Money
from app.schemas.transaction import TransactionOut


class HistoryDay(BaseModel):
    date: date
    total_expenses: Money = Field(description="All expenses on this day (regardless of filter).")
    transactions: list[TransactionOut] = Field(description="Newest first; filtered by `type`.")


class MonthlyHistory(BaseModel):
    year: int
    month: int
    entry_count: int = Field(description="All transactions in the month (unfiltered).")
    total_expenses: Money
    total_income: Money
    days: list[HistoryDay] = Field(description="Days with matching transactions, newest first.")
