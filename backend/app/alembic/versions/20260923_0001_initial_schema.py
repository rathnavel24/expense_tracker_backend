"""Initial schema: users, sessions, categories (seeded), transactions.

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transaction_type = postgresql.ENUM("expense", "income", name="transaction_type", create_type=False)

# (kind, slug, name, icon, color token). `color` is a palette token the frontend maps to
# light/dark values; `icon` is a key the frontend maps to an icon component.
SEED_CATEGORIES = [
    ("expense", "food", "Food", "utensils", "orange"),
    ("expense", "transport", "Transport", "bus", "blue"),
    ("expense", "shopping", "Shopping", "shopping-bag", "magenta"),
    ("expense", "bills", "Bills", "receipt", "violet"),
    ("expense", "entertainment", "Entertainment", "clapperboard", "yellow"),
    ("expense", "health", "Health", "heart-pulse", "red"),
    ("expense", "education", "Education", "graduation-cap", "aqua"),
    ("expense", "other", "Other", "shapes", "gray"),
    ("income", "salary", "Salary", "briefcase", "green"),
    ("income", "freelance", "Freelance", "laptop", "green"),
    ("income", "business", "Business", "store", "green"),
    ("income", "interest", "Interest", "landmark", "green"),
    ("income", "gift", "Gift", "gift", "green"),
    ("income", "refund", "Refund", "undo", "green"),
    ("income", "other", "Other", "shapes", "green"),
]


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    transaction_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_auth_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    categories = op.create_table(
        "categories",
        sa.Column("id", sa.SmallInteger(), sa.Identity(), nullable=False),
        sa.Column("kind", transaction_type, nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("id", "kind", name="uq_categories_id_kind"),
        sa.UniqueConstraint("kind", "slug", name="uq_categories_kind_slug"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("category_id", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.String(200), server_default="", nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_transactions_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "type"],
            ["categories.id", "categories.kind"],
            name="fk_transactions_category_kind",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )
    op.create_index(
        "ix_transactions_user_date", "transactions", ["user_id", "occurred_on", "created_at", "id"]
    )
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])

    order_by_kind: dict[str, int] = {}
    rows = []
    for kind, slug, name, icon, color in SEED_CATEGORIES:
        order_by_kind[kind] = order_by_kind.get(kind, 0) + 1
        rows.append(
            {
                "kind": kind,
                "slug": slug,
                "name": name,
                "icon": icon,
                "color": color,
                "sort_order": order_by_kind[kind],
            }
        )
    op.bulk_insert(categories, rows)


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("auth_sessions")
    op.drop_table("users")
    transaction_type.drop(op.get_bind(), checkfirst=True)
