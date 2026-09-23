from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Money travels as a JSON *string* ("1250.00") so no client ever parses it as a float.
Money = Annotated[
    Decimal,
    Field(max_digits=12, decimal_places=2, examples=["1250.00"]),
]
PositiveMoney = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2, examples=["250.00"]),
]

MIN_DATE = date(2000, 1, 1)
MAX_DATE = date(2100, 12, 31)


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Transaction not found."])
    fields: dict[str, str] | None = Field(default=None, examples=[{"amount": "Must be > 0"}])


class ErrorResponse(BaseModel):
    error: ErrorDetail
