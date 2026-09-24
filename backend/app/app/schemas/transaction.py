import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.models.category import TransactionType
from app.models.transaction import PaymentMethod
from app.schemas.category import CategoryOut
from app.schemas.common import MAX_DATE, MIN_DATE, PositiveMoney, Schema

Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


def check_payment_method(
    method: PaymentMethod | None, info: ValidationInfo
) -> PaymentMethod | None:
    """Field validator body: `type` is declared before `payment_method`, so it's in info.data."""
    if info.data.get("type") is TransactionType.INCOME and method is not None:
        raise ValueError("Income cannot have a payment method.")
    return method


def check_date(value: date) -> date:
    if not MIN_DATE <= value <= MAX_DATE:
        raise ValueError(f"Date must be between {MIN_DATE.year} and {MAX_DATE.year}.")
    return value


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: PositiveMoney
    category_id: int = Field(gt=0, description="An expense category or income source id.")
    description: Description = ""
    occurred_on: date = Field(description="Calendar date (YYYY-MM-DD); no time or timezone.")
    payment_method: PaymentMethod | None = Field(
        default=None, description="Expenses only: how it was paid."
    )

    @field_validator("occurred_on")
    @classmethod
    def _date_range(cls, value: date) -> date:
        return check_date(value)

    @field_validator("payment_method")
    @classmethod
    def _payment_method(
        cls, value: PaymentMethod | None, info: ValidationInfo
    ) -> PaymentMethod | None:
        return check_payment_method(value, info)


# Fields that may be explicitly set to null in a PATCH.
NULLABLE_FIELDS = frozenset({"payment_method"})


class TransactionUpdate(BaseModel):
    """Partial update. Omitted fields are left unchanged; only `payment_method` may be null.
    Changing `type` to income clears the payment method."""

    type: TransactionType | None = None
    amount: PositiveMoney | None = None
    category_id: int | None = Field(default=None, gt=0)
    description: Description | None = None
    occurred_on: date | None = None
    payment_method: PaymentMethod | None = None

    @field_validator("occurred_on")
    @classmethod
    def _date_range(cls, value: date | None) -> date | None:
        return None if value is None else check_date(value)

    @model_validator(mode="after")
    def _no_nulls(self) -> Self:
        for name in self.model_fields_set - NULLABLE_FIELDS:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be null.")
        return self


class TransactionOut(Schema):
    id: uuid.UUID
    type: TransactionType
    amount: PositiveMoney
    category: CategoryOut
    description: str
    occurred_on: date
    payment_method: PaymentMethod | None
    recurring_rule_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    next_cursor: str | None = Field(
        description="Pass as `cursor` to fetch the next page; null when there are no more."
    )
