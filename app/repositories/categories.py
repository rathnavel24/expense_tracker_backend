from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, TransactionType


def list_active(db: Session, kind: TransactionType | None = None) -> Sequence[Category]:
    stmt = select(Category).where(Category.is_active).order_by(Category.kind, Category.sort_order)
    if kind is not None:
        stmt = stmt.where(Category.kind == kind)
    return db.scalars(stmt).all()


def get(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)
