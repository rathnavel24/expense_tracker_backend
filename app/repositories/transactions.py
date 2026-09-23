"""Transaction queries. Every function takes `user_id` and filters on it - there is no way
to read or modify a transaction without proving ownership through the query itself."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Row, and_, func, select, tuple_
from sqlalchemy.orm import Session

from app.models import Category, PaymentMethod, Transaction, TransactionType

_NEWEST_FIRST = (
    Transaction.occurred_on.desc(),
    Transaction.created_at.desc(),
    Transaction.id.desc(),
)


@dataclass(frozen=True, slots=True)
class Cursor:
    """Keyset position: the sort key of the last item on the previous page."""

    occurred_on: date
    created_at: datetime
    id: uuid.UUID


def get(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction | None:
    return db.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )


def list_page(
    db: Session,
    user_id: uuid.UUID,
    *,
    limit: int,
    type_: TransactionType | None = None,
    start: date | None = None,
    end: date | None = None,
    after: Cursor | None = None,
) -> Sequence[Transaction]:
    """Newest-first page of transactions. `end` is exclusive."""
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if type_ is not None:
        stmt = stmt.where(Transaction.type == type_)
    if start is not None:
        stmt = stmt.where(Transaction.occurred_on >= start)
    if end is not None:
        stmt = stmt.where(Transaction.occurred_on < end)
    if after is not None:
        stmt = stmt.where(
            tuple_(Transaction.occurred_on, Transaction.created_at, Transaction.id)
            < tuple_(after.occurred_on, after.created_at, after.id)
        )
    return db.scalars(stmt.order_by(*_NEWEST_FIRST).limit(limit)).all()


def add(db: Session, transaction: Transaction) -> Transaction:
    db.add(transaction)
    db.flush()
    return transaction


def delete(db: Session, transaction: Transaction) -> None:
    db.delete(transaction)
    db.flush()


@dataclass(frozen=True, slots=True)
class TypeTotal:
    amount: Decimal
    count: int


def totals_by_type(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[TransactionType, TypeTotal]:
    rows = db.execute(
        select(Transaction.type, func.sum(Transaction.amount), func.count())
        .where(
            Transaction.user_id == user_id,
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        .group_by(Transaction.type)
    ).all()
    return {row[0]: TypeTotal(amount=row[1], count=row[2]) for row in rows}


def expense_totals_by_category(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> Sequence[Row[tuple[Category, Decimal, int]]]:
    """(category, amount, count) per expense category with spending, largest first."""
    total = func.sum(Transaction.amount).label("total")
    return db.execute(
        select(Category, total, func.count(Transaction.id))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            and_(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.occurred_on >= start,
                Transaction.occurred_on < end,
            )
        )
        .group_by(Category.id)
        .order_by(total.desc(), Category.sort_order)
    ).all()


def expense_totals_by_day(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[date, Decimal]:
    rows = db.execute(
        select(Transaction.occurred_on, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        .group_by(Transaction.occurred_on)
    ).all()
    return {row[0]: row[1] for row in rows}


def expense_totals_by_payment_method(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> Sequence[Row[tuple[PaymentMethod | None, Decimal, int]]]:
    total = func.sum(Transaction.amount).label("total")
    return db.execute(
        select(Transaction.payment_method, total, func.count())
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        .group_by(Transaction.payment_method)
        .order_by(total.desc())
    ).all()


def totals_by_month(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[tuple[int, int, TransactionType], Decimal]:
    """{(year, month, type): total} for every month with activity in [start, end)."""
    year = func.extract("year", Transaction.occurred_on).label("y")
    month = func.extract("month", Transaction.occurred_on).label("m")
    rows = db.execute(
        select(year, month, Transaction.type, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.occurred_on >= start,
            Transaction.occurred_on < end,
        )
        .group_by(year, month, Transaction.type)
    ).all()
    return {(int(r[0]), int(r[1]), r[2]): r[3] for r in rows}
