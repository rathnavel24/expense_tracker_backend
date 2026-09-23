import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models.category import TransactionType
from app.schemas.category import CategoryOut
from app.schemas.common import MAX_DATE, MIN_DATE, PositiveMoney, Schema

Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]


def _check_date(value: date) -> date:
    if not MIN_DATE <= value <= MAX_DATE:
        raise ValueError(f"Date must be between {MIN_DATE.year} and {MAX_DATE.year}.")
    return value


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: PositiveMoney
    category_id: int = Field(gt=0, description="An expense category or income source id.")
    description: Description = ""
    occurred_on: date = Field(description="Calendar date (YYYY-MM-DD); no time or timezone.")

    @field_validator("occurred_on")
    @classmethod
    def _date_range(cls, value: date) -> date:
        return _check_date(value)


class TransactionUpdate(BaseModel):
    """Partial update. Omitted fields are left unchanged; `null` is not accepted."""

    type: TransactionType | None = None
    amount: PositiveMoney | None = None
    category_id: int | None = Field(default=None, gt=0)
    description: Description | None = None
    occurred_on: date | None = None

    @field_validator("occurred_on")
    @classmethod
    def _date_range(cls, value: date | None) -> date | None:
        return None if value is None else _check_date(value)

    @model_validator(mode="after")
    def _no_nulls(self) -> Self:
        for name in self.model_fields_set:
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
    created_at: datetime
    updated_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    next_cursor: str | None = Field(
        description="Pass as `cursor` to fetch the next page; null when there are no more."
    )
