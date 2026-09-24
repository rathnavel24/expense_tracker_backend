import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.transaction import PaymentMethod
from app.schemas.common import Schema


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserOut(Schema):
    id: uuid.UUID
    email: str
    name: str
    last_payment_method: PaymentMethod | None
