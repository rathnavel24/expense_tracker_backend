from pydantic import BaseModel, Field

from app.schemas.category import CategoryOut
from app.schemas.common import Money
from app.schemas.transaction import TransactionOut


class CategoryTotal(BaseModel):
    category: CategoryOut
    amount: Money
    count: int


class MonthlyDashboard(BaseModel):
    year: int
    month: int = Field(ge=1, le=12)
    total_income: Money
    total_expenses: Money
    income_count: int
    expense_count: int
    expense_breakdown: list[CategoryTotal] = Field(
        description="Expense totals per category for the month, largest first."
    )
    recent_transactions: list[TransactionOut] = Field(
        description="Most recent transactions in the month, newest first."
    )
