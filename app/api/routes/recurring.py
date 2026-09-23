import uuid

from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.api.responses import NOT_FOUND, UNAUTHORIZED, VALIDATION
from app.schemas.recurring import RecurringCreate, RecurringOut, RecurringUpdate
from app.services import recurring

router = APIRouter(prefix="/recurring", tags=["recurring"], responses=UNAUTHORIZED)


@router.get("", response_model=list[RecurringOut], summary="List recurring entries")
def list_recurring(user: CurrentUser, db: DB) -> list[RecurringOut]:
    return [RecurringOut.model_validate(r) for r in recurring.list_rules(db, user)]


@router.post(
    "",
    response_model=RecurringOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a monthly recurring entry",
    description="Occurrences from `start_on` up to today are created immediately.",
    responses=VALIDATION,
)
def create_recurring(body: RecurringCreate, user: CurrentUser, db: DB) -> RecurringOut:
    return RecurringOut.model_validate(recurring.create(db, user, body))


@router.get(
    "/{rule_id}", response_model=RecurringOut, summary="Get a recurring entry", responses=NOT_FOUND
)
def get_recurring(rule_id: uuid.UUID, user: CurrentUser, db: DB) -> RecurringOut:
    return RecurringOut.model_validate(recurring.get(db, user, rule_id))


@router.patch(
    "/{rule_id}",
    response_model=RecurringOut,
    summary="Update, pause or resume a recurring entry",
    description="Affects future occurrences only.",
    responses={**NOT_FOUND, **VALIDATION},
)
def update_recurring(
    rule_id: uuid.UUID, body: RecurringUpdate, user: CurrentUser, db: DB
) -> RecurringOut:
    return RecurringOut.model_validate(recurring.update(db, user, rule_id, body))


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recurring entry",
    description="Stops future occurrences; transactions already created are kept.",
    responses=NOT_FOUND,
)
def delete_recurring(rule_id: uuid.UUID, user: CurrentUser, db: DB) -> None:
    recurring.delete(db, user, rule_id)
