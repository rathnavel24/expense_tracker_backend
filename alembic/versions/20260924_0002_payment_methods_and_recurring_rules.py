"""Payment methods on expenses; monthly recurring rules.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

payment_method = postgresql.ENUM(
    "cash", "upi", "card", "bank", name="payment_method", create_type=False
)
transaction_type = postgresql.ENUM("expense", "income", name="transaction_type", create_type=False)

EXPENSE_ONLY = "type = 'expense' OR payment_method IS NULL"


def upgrade() -> None:
    payment_method.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category_id", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.String(200), server_default="", nullable=False),
        sa.Column("payment_method", payment_method, nullable=True),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=False),
        sa.Column("start_on", sa.Date(), nullable=False),
        sa.Column("next_run_on", sa.Date(), nullable=False),
        sa.Column("last_run_on", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_recurring_rules_amount_positive"),
        sa.CheckConstraint(
            "day_of_month BETWEEN 1 AND 31", name="ck_recurring_rules_day_of_month_range"
        ),
        sa.CheckConstraint(EXPENSE_ONLY, name="ck_recurring_rules_payment_method_expense_only"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_recurring_rules_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "type"],
            ["categories.id", "categories.kind"],
            name="fk_recurring_rules_category_kind",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_rules"),
    )
    op.create_index("ix_recurring_rules_user_id", "recurring_rules", ["user_id"])
    op.create_index(
        "ix_recurring_rules_due",
        "recurring_rules",
        ["user_id", "next_run_on"],
        postgresql_where=sa.text("is_active"),
    )

    op.add_column("transactions", sa.Column("payment_method", payment_method, nullable=True))
    op.add_column("transactions", sa.Column("recurring_rule_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_transactions_payment_method_expense_only", "transactions", EXPENSE_ONLY
    )
    op.create_foreign_key(
        "fk_transactions_recurring_rule_id_recurring_rules",
        "transactions",
        "recurring_rules",
        ["recurring_rule_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_transactions_recurring_occurrence",
        "transactions",
        ["recurring_rule_id", "occurred_on"],
        unique=True,
        postgresql_where=sa.text("recurring_rule_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_transactions_recurring_occurrence", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_recurring_rule_id_recurring_rules", "transactions", type_="foreignkey"
    )
    op.drop_constraint("ck_transactions_payment_method_expense_only", "transactions", type_="check")
    op.drop_column("transactions", "recurring_rule_id")
    op.drop_column("transactions", "payment_method")
    op.drop_table("recurring_rules")
    payment_method.drop(op.get_bind(), checkfirst=True)
