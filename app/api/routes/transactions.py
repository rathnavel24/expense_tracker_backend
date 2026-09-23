import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DB, CurrentUser, SyncedUser
from app.api.responses import NOT_FOUND, UNAUTHORIZED, VALIDATION
from app.core.errors import ValidationFailedError
from app.models import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)
from app.services import transactions
from app.services.months import month_range

router = APIRouter(prefix="/transactions", tags=["transactions"], responses=UNAUTHORIZED)


@router.get(
    "",
    response_model=TransactionPage,
    summary="List transactions",
    description="Newest first, with cursor pagination. Optionally filter by type and/or month.",
    responses=VALIDATION,
)
def list_transactions(
    user: SyncedUser,
    db: DB,
    type: TransactionType | None = None,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> TransactionPage:
    if (year is None) != (month is None):
        raise ValidationFailedError(
            "Provide both year and month.", fields={"month": "Provide both year and month."}
        )
    start, end = month_range(year, month) if year and month else (None, None)
    return transactions.list_page(
        db, user, limit=limit, type_=type, start=start, end=end, cursor=cursor
    )


@router.post(
    "",
    response_model=TransactionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record an expense or income",
    responses=VALIDATION,
)
def create_transaction(body: TransactionCreate, user: CurrentUser, db: DB) -> TransactionOut:
    return TransactionOut.model_validate(transactions.create(db, user, body))


@router.get(
    "/{transaction_id}",
    response_model=TransactionOut,
    summary="Get a transaction",
    responses=NOT_FOUND,
)
def get_transaction(transaction_id: uuid.UUID, user: CurrentUser, db: DB) -> TransactionOut:
    return TransactionOut.model_validate(transactions.get(db, user, transaction_id))


@router.patch(
    "/{transaction_id}",
    response_model=TransactionOut,
    summary="Update a transaction",
    description="Partial update. Changing `type` also requires a matching `category_id`.",
    responses={**NOT_FOUND, **VALIDATION},
)
def update_transaction(
    transaction_id: uuid.UUID, body: TransactionUpdate, user: CurrentUser, db: DB
) -> TransactionOut:
    return TransactionOut.model_validate(transactions.update(db, user, transaction_id, body))


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
    responses=NOT_FOUND,
)
def delete_transaction(transaction_id: uuid.UUID, user: CurrentUser, db: DB) -> None:
    transactions.delete(db, user, transaction_id)
