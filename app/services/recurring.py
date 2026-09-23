import uuid

from sqlalchemy.orm import Session

from app.core.clock import today as app_today
from app.core.errors import NotFoundError
from app.models import RecurringRule, User
from app.repositories import recurring
from app.schemas.recurring import RecurringCreate, RecurringUpdate
from app.services.entry_rules import apply_type_and_category, resolve_category
from app.services.recurrence import (
    first_occurrence_on_or_after,
    next_occurrence_after,
    occurrence_in_month_after,
)

# Bounds one catch-up pass (e.g. a rule started years ago); the rest follow on later reads.
MAX_OCCURRENCES_PER_PASS = 36
_NOT_FOUND = "Recurring entry not found."


def generate_due(db: Session, user: User) -> None:
    """Create every transaction that recurring rules owe up to today, then commit.

    There is no scheduler: this runs at the start of any request that reads transaction
    data, so totals are always up to date when viewed. It is cheap when nothing is due
    (one indexed query) and idempotent under concurrency.
    """
    today = app_today()
    rules = recurring.lock_due(db, user.id, today)
    if not rules:
        db.rollback()  # release the (empty) transaction
        return
    for rule in rules:
        for _ in range(MAX_OCCURRENCES_PER_PASS):
            if rule.next_run_on > today:
                break
            recurring.insert_occurrence(db, rule, rule.next_run_on)
            rule.last_run_on = rule.next_run_on
            rule.next_run_on = next_occurrence_after(rule.next_run_on, rule.day_of_month)
    db.commit()


def list_rules(db: Session, user: User) -> list[RecurringRule]:
    return list(recurring.list_for_user(db, user.id))


def get(db: Session, user: User, rule_id: uuid.UUID) -> RecurringRule:
    rule = recurring.get(db, user.id, rule_id)
    if rule is None:
        raise NotFoundError(_NOT_FOUND)
    return rule


def create(db: Session, user: User, data: RecurringCreate) -> RecurringRule:
    category = resolve_category(db, data.category_id, data.type)
    rule = recurring.add(
        db,
        RecurringRule(
            user_id=user.id,
            type=data.type,
            amount=data.amount,
            category_id=category.id,
            description=data.description,
            payment_method=data.payment_method,
            day_of_month=data.start_on.day,
            start_on=data.start_on,
            next_run_on=data.start_on,
        ),
    )
    db.commit()
    generate_due(db, user)
    db.refresh(rule)
    return rule


def update(db: Session, user: User, rule_id: uuid.UUID, data: RecurringUpdate) -> RecurringRule:
    rule = get(db, user, rule_id)
    changes = data.model_dump(exclude_unset=True)
    apply_type_and_category(
        db, changes, current_type=rule.type, current_category_id=rule.category_id
    )

    resuming = changes.get("is_active") is True and not rule.is_active
    new_day = changes.get("day_of_month")
    for field, value in changes.items():
        setattr(rule, field, value)

    today = app_today()
    if new_day is not None:
        # Move to the new day without ever generating twice in a month already covered.
        rule.next_run_on = (
            occurrence_in_month_after(rule.last_run_on, rule.day_of_month)
            if rule.last_run_on
            else first_occurrence_on_or_after(rule.start_on, rule.day_of_month)
        )
    if resuming:
        # Don't backfill the months it was paused for.
        rule.next_run_on = max(
            rule.next_run_on, first_occurrence_on_or_after(today, rule.day_of_month)
        )
    db.commit()
    generate_due(db, user)
    db.refresh(rule)
    return rule


def delete(db: Session, user: User, rule_id: uuid.UUID) -> None:
    """Stops future occurrences. Transactions already created are kept."""
    recurring.delete(db, get(db, user, rule_id))
    db.commit()
