import enum

from sqlalchemy import Enum, Identity, SmallInteger, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TransactionType(enum.StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


# Shared Postgres enum type, used by both categories.kind and transactions.type.
transaction_type_enum = Enum(
    TransactionType,
    name="transaction_type",
    values_callable=lambda e: [m.value for m in e],
)


class Category(TimestampMixin, Base):
    """Expense categories (Food, Transport, ...) and income sources (Salary, Freelance, ...).

    Both are the same concept - "what bucket does this money belong to" - distinguished by
    `kind`. Categories are global reference data seeded by migrations.
    """

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("kind", "slug"),
        # Target of the composite FK on transactions(category_id, type): lets Postgres
        # guarantee an expense can only use an expense category, and income an income source.
        UniqueConstraint("id", "kind"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, Identity(), primary_key=True)
    kind: Mapped[TransactionType] = mapped_column(transaction_type_enum, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # Presentation hints, as keys the frontend maps to an icon and a light/dark color pair.
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())
