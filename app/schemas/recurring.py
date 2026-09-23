import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from app.models.category import TransactionType
from app.models.transaction import PaymentMethod
from app.schemas.category import CategoryOut
from app.schemas.common import PositiveMoney, Schema
from app.schemas.transaction import NULLABLE_FIELDS, Description, check_date, check_payment_method


class RecurringCreate(BaseModel):
    type: TransactionType
    amount: PositiveMoney
    category_id: int = Field(gt=0)
    description: Description = ""
    payment_method: PaymentMethod | None = None
    start_on: date = Field(
        description="Date of the first occurrence. Its day of month is used every month "
        "(clamped to shorter months). Occurrences due up to today are created immediately."
    )

    @field_validator("start_on")
    @classmethod
    def _date_range(cls, value: date) -> date:
        return check_date(value)

    @field_validator("payment_method")
    @classmethod
    def _payment_method(
        cls, value: PaymentMethod | None, info: ValidationInfo
    ) -> PaymentMethod | None:
        return check_payment_method(value, info)


class RecurringUpdate(BaseModel):
    """Partial update. Changes apply to future occurrences only."""

    type: TransactionType | None = None
    amount: PositiveMoney | None = None
    category_id: int | None = Field(default=None, gt=0)
    description: Description | None = None
    payment_method: PaymentMethod | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    is_active: bool | None = Field(
        default=None, description="Pause (false) or resume (true). Resuming skips missed months."
    )

    @model_validator(mode="after")
    def _no_nulls(self) -> Self:
        for name in self.model_fields_set - NULLABLE_FIELDS:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be null.")
        return self


class RecurringOut(Schema):
    id: uuid.UUID
    type: TransactionType
    amount: PositiveMoney
    category: CategoryOut
    description: str
    payment_method: PaymentMethod | None
    day_of_month: int
    start_on: date
    next_run_on: date = Field(description="Next date a transaction will be created.")
    last_run_on: date | None = Field(description="Most recent generated occurrence.")
    is_active: bool
    created_at: datetime
    updated_at: datetime
