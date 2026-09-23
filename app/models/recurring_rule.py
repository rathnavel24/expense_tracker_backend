import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.category import Category, TransactionType, transaction_type_enum
from app.models.transaction import (
    MONEY,
    PAYMENT_METHOD_EXPENSE_ONLY,
    PaymentMethod,
    payment_method_enum,
)


class RecurringRule(TimestampMixin, Base):
    """A monthly template (rent, a subscription, salary) that generates transactions.

    Occurrences fall on `day_of_month`, clamped to the month's last day (31 -> 30 Sep,
    28/29 Feb) without drifting. `next_run_on` is the next date still to be generated;
    generation is idempotent thanks to the unique (recurring_rule_id, occurred_on) index on
    transactions.
    """

    __tablename__ = "recurring_rules"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="day_of_month_range"),
        CheckConstraint(PAYMENT_METHOD_EXPENSE_ONLY, name="payment_method_expense_only"),
        ForeignKeyConstraint(
            ["category_id", "type"],
            ["categories.id", "categories.kind"],
            name="fk_recurring_rules_category_kind",
        ),
        Index("ix_recurring_rules_user_id", "user_id"),
        # Finds rules that are due, on every read of transaction data.
        Index(
            "ix_recurring_rules_due",
            "user_id",
            "next_run_on",
            postgresql_where=text("is_active"),
        ),
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
    payment_method: Mapped[PaymentMethod | None] = mapped_column(payment_method_enum)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_on: Mapped[date] = mapped_column(Date, nullable=False)
    next_run_on: Mapped[date] = mapped_column(Date, nullable=False)
    last_run_on: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    category: Mapped[Category] = relationship(lazy="joined")
