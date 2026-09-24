import base64
import binascii
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationFailedError
from app.models import Transaction, TransactionType, User
from app.repositories import transactions
from app.repositories.transactions import Cursor
from app.schemas.transaction import TransactionCreate, TransactionPage, TransactionUpdate
from app.services.entry_rules import (
    apply_type_and_category,
    remember_payment_method,
    resolve_category,
)

_NOT_FOUND = "Transaction not found."


def get(db: Session, user: User, transaction_id: uuid.UUID) -> Transaction:
    transaction = transactions.get(db, user.id, transaction_id)
    if transaction is None:
        # Same response whether it doesn't exist or belongs to someone else.
        raise NotFoundError(_NOT_FOUND)
    return transaction


def create(db: Session, user: User, data: TransactionCreate) -> Transaction:
    category = resolve_category(db, data.category_id, data.type)
    transaction = transactions.add(
        db,
        Transaction(
            user_id=user.id,
            type=data.type,
            amount=data.amount,
            category_id=category.id,
            description=data.description,
            occurred_on=data.occurred_on,
            payment_method=data.payment_method,
        ),
    )
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
    remember_payment_method(user, changes.get("payment_method"))
    db.commit()
    db.refresh(transaction)
    return transaction


def delete(db: Session, user: User, transaction_id: uuid.UUID) -> None:
    transactions.delete(db, get(db, user, transaction_id))
    db.commit()


# --- Listing ---------------------------------------------------------------------------


def _encode_cursor(t: Transaction) -> str:
    raw = f"{t.occurred_on.isoformat()}|{t.created_at.isoformat()}|{t.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor(value: str) -> Cursor:
    try:
        padded = value + "=" * (-len(value) % 4)
        occurred_on, created_at, id_ = base64.urlsafe_b64decode(padded).decode().split("|")
        return Cursor(
            occurred_on=date.fromisoformat(occurred_on),
            created_at=datetime.fromisoformat(created_at),
            id=uuid.UUID(id_),
        )
    except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
        raise ValidationFailedError(
            "Invalid cursor.", fields={"cursor": "Invalid pagination cursor."}
        ) from exc


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
    rows = transactions.list_page(
        db,
        user.id,
        limit=limit + 1,
        type_=type_,
        start=start,
        end=end,
        after=_decode_cursor(cursor) if cursor else None,
    )
    items = list(rows[:limit])
    next_cursor = _encode_cursor(items[-1]) if len(rows) > limit else None
    return TransactionPage.model_validate({"items": items, "next_cursor": next_cursor})
