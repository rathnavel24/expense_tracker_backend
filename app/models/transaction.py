import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.category import Category, TransactionType, transaction_type_enum

# NUMERIC(12, 2): exact decimal, up to 99,99,99,99,999.99 - far beyond personal use.
MONEY = Numeric(12, 2)


class Transaction(TimestampMixin, Base):
    """A single expense or income entry.

    Expenses and income share one table because they share every column and are almost
    always read together (history, recent activity, monthly totals). `type` distinguishes
    them, and the composite foreign key below makes a mismatched category impossible.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        ForeignKeyConstraint(
            ["category_id", "type"],
            ["categories.id", "categories.kind"],
            name="fk_transactions_category_kind",
        ),
        # Serves every hot query: per-user month ranges, newest-first listings and
        # keyset pagination on (occurred_on, created_at, id).
        Index("ix_transactions_user_date", "user_id", "occurred_on", "created_at", "id"),
        # Supports the FK and the per-category breakdown.
        Index("ix_transactions_category_id", "category_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(transaction_type_enum, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    category_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    description: Mapped[str] = mapped_column(
        String(200), nullable=False, default="", server_default=""
    )
    # A calendar date, not a timestamp: "23 September" must stay 23 September in every zone.
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)

    category: Mapped[Category] = relationship(lazy="joined")
