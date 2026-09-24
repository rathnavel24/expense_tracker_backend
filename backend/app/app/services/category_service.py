from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailedError
from app.models import Category, PaymentMethod, TransactionType


def list_active(db: Session, kind: TransactionType | None = None) -> Sequence[Category]:
    stmt = select(Category).where(Category.is_active).order_by(Category.kind, Category.sort_order)
    if kind is not None:
        stmt = stmt.where(Category.kind == kind)
    return db.scalars(stmt).all()


def resolve_category(db: Session, category_id: int, type_: TransactionType) -> Category:
    """The category must exist, be active and match the entry type.

    Postgres enforces the type match too (composite FK); checking here turns what would be
    an integrity error into a clear field-level message.
    """
    category = db.get(Category, category_id)
    if category is None or not category.is_active:
        raise ValidationFailedError(
            "Invalid category.", fields={"category_id": "This category does not exist."}
        )
    if category.kind != type_:
        label = "an expense category" if type_ is TransactionType.EXPENSE else "an income source"
        raise ValidationFailedError("Invalid category.", fields={"category_id": f"Choose {label}."})
    return category


def apply_type_and_category(
    db: Session,
    changes: dict[str, object],
    *,
    current_type: TransactionType,
    current_category_id: int,
) -> None:
    """Validate a PATCH's type/category/payment-method changes against the current entry
    (a transaction or a recurring rule).

    Mutates `changes` in place: switching to income clears the payment method.
    """
    new_type = changes.get("type", current_type)
    assert isinstance(new_type, TransactionType)

    if "type" in changes or "category_id" in changes:
        if new_type != current_type and "category_id" not in changes:
            raise ValidationFailedError(
                "Invalid category.",
                fields={"category_id": "Choose a category for the new transaction type."},
            )
        new_category_id = changes.get("category_id", current_category_id)
        assert isinstance(new_category_id, int)
        # An existing (possibly since-retired) category stays valid if unchanged.
        if new_category_id != current_category_id or new_type != current_type:
            resolve_category(db, new_category_id, new_type)

    if new_type is TransactionType.INCOME:
        if isinstance(changes.get("payment_method"), PaymentMethod):
            raise ValidationFailedError(
                "Invalid payment method.",
                fields={"payment_method": "Income cannot have a payment method."},
            )
        changes["payment_method"] = None
