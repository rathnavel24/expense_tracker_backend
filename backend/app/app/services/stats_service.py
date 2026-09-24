"""Aggregate queries (totals by type, category, day, payment method, month) used by the
dashboard, history and insights. Every query is scoped to one user."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Row, and_, func, select
from sqlalchemy.orm import Session

from app.models import Category, PaymentMethod, Transaction, TransactionType


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
