import uuid

from sqlalchemy import String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.transaction import PaymentMethod, payment_method_enum


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    # Stored lower-cased; uniqueness is therefore case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Pre-selected in the expense form; follows the user across devices.
    last_payment_method: Mapped[PaymentMethod | None] = mapped_column(payment_method_enum)
