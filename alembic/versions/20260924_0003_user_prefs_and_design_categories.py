"""Remember each user's last payment method; align category icons with the v2 design.

Business and Interest income sources are retired (hidden, not deleted), so existing
transactions that use them stay valid.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

payment_method = postgresql.ENUM(
    "cash", "upi", "card", "bank", name="payment_method", create_type=False
)

# (kind, slug) -> (new icon, new sort order, active); old values for downgrade.
CHANGES = {
    ("expense", "food"): (("utensils", 1, True), ("utensils", 1, True)),
    ("expense", "transport"): (("car", 2, True), ("bus", 2, True)),
    ("expense", "shopping"): (("shopping-bag", 3, True), ("shopping-bag", 3, True)),
    ("expense", "bills"): (("lightbulb", 4, True), ("receipt", 4, True)),
    ("expense", "entertainment"): (("ticket", 5, True), ("clapperboard", 5, True)),
    ("expense", "health"): (("heart-pulse", 6, True), ("heart-pulse", 6, True)),
    ("expense", "education"): (("book-open", 7, True), ("graduation-cap", 7, True)),
    ("expense", "other"): (("package", 8, True), ("shapes", 8, True)),
    ("income", "salary"): (("briefcase", 1, True), ("briefcase", 1, True)),
    ("income", "freelance"): (("laptop", 2, True), ("laptop", 2, True)),
    ("income", "gift"): (("gift", 3, True), ("gift", 5, True)),
    ("income", "refund"): (("undo", 4, True), ("undo", 6, True)),
    ("income", "other"): (("trending-up", 5, True), ("shapes", 7, True)),
    ("income", "business"): (("store", 90, False), ("store", 3, True)),
    ("income", "interest"): (("landmark", 91, False), ("landmark", 4, True)),
}

_update = sa.text(
    "UPDATE categories SET icon = :icon, sort_order = :sort_order, is_active = :active "
    "WHERE kind = CAST(:kind AS transaction_type) AND slug = :slug"
)


def _apply(new: bool) -> None:
    for (kind, slug), (after, before) in CHANGES.items():
        icon, sort_order, active = after if new else before
        op.execute(
            _update.bindparams(
                icon=icon, sort_order=sort_order, active=active, kind=kind, slug=slug
            )
        )


def upgrade() -> None:
    op.add_column("users", sa.Column("last_payment_method", payment_method, nullable=True))
    _apply(new=True)


def downgrade() -> None:
    _apply(new=False)
    op.drop_column("users", "last_payment_method")
