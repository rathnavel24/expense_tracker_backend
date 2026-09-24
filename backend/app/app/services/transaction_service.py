"""Transactions: CRUD and listing. Every query filters on the owner's `user_id`, so there is
no way to read or change a transaction without owning it."""

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import PaymentMethod, Transaction, TransactionType, User
from app.schemas.transaction import TransactionCreate, TransactionPage, TransactionUpdate
from app.services.category_service import apply_type_and_category, resolve_category
from app.utils import Cursor, decode_cursor, encode_cursor

_NOT_FOUND = "Transaction not found."

NEWEST_FIRST = (
    Transaction.occurred_on.desc(),
    Transaction.created_at.desc(),
    Transaction.id.desc(),
)


def remember_payment_method(user: User, method: PaymentMethod | None) -> None:
    """Keep the user's most recently used payment method, to pre-select it next time."""
    if method is not None:
        user.last_payment_method = method


def fetch_transactions(
    db: Session,
    user_id: uuid.UUID,
    *,
    limit: int,
    type_: TransactionType | None = None,
    start: date | None = None,
    end: date | None = None,
    after: Cursor | None = None,
) -> Sequence[Transaction]:
    """Newest-first transactions, optionally filtered. `end` is exclusive."""
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
    return db.scalars(stmt.order_by(*NEWEST_FIRST).limit(limit)).all()


def get(db: Session, user: User, transaction_id: uuid.UUID) -> Transaction:
    transaction = db.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user.id)
    )
    if transaction is None:
        # Same response whether it doesn't exist or belongs to someone else.
        raise NotFoundError(_NOT_FOUND)
    return transaction


def create(db: Session, user: User, data: TransactionCreate) -> Transaction:
    category = resolve_category(db, data.category_id, data.type)
    transaction = Transaction(
        user_id=user.id,
        type=data.type,
        amount=data.amount,
        category_id=category.id,
        description=data.description,
        occurred_on=data.occurred_on,
        payment_method=data.payment_method,
    )
    db.add(transaction)
    remember_payment_method(user, data.payment_method)
    db.commit()
    db.refresh(transaction)
    return transaction


def update(
    db: Session, user: User, transaction_id: uuid.UUID, data: TransactionUpdate
) -> Transaction:
    transaction = get(db, user, transaction_id)
    changes = data.model_dump(exclude_unset=True)
    apply_type_and_category(
        db, changes, current_type=transaction.type, current_category_id=transaction.category_id
    )
    for field, value in changes.items():
        setattr(transaction, field, value)
    remember_payment_method(user, changes.get("payment_method"))  # type: ignore[arg-type]
    db.commit()
    db.refresh(transaction)
    return transaction


def delete(db: Session, user: User, transaction_id: uuid.UUID) -> None:
    db.delete(get(db, user, transaction_id))
    db.commit()


def list_page(
    db: Session,
    user: User,
    *,
    limit: int,
    type_: TransactionType | None,
    start: date | None,
    end: date | None,
    cursor: str | None,
) -> TransactionPage:
    # Fetch one extra row to know whether another page exists.
    rows = fetch_transactions(
        db,
        user.id,
        limit=limit + 1,
        type_=type_,
        start=start,
        end=end,
        after=decode_cursor(cursor) if cursor else None,
    )
    items = list(rows[:limit])
    last = items[-1] if items else None
    next_cursor = (
        encode_cursor(last.occurred_on, last.created_at, last.id)
        if last is not None and len(rows) > limit
        else None
    )
    return TransactionPage.model_validate({"items": items, "next_cursor": next_cursor})
