import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import RecurringRule, Transaction


def list_for_user(db: Session, user_id: uuid.UUID) -> Sequence[RecurringRule]:
    return db.scalars(
        select(RecurringRule)
        .where(RecurringRule.user_id == user_id)
        .order_by(
            RecurringRule.is_active.desc(), RecurringRule.day_of_month, RecurringRule.created_at
        )
    ).all()


def get(db: Session, user_id: uuid.UUID, rule_id: uuid.UUID) -> RecurringRule | None:
    return db.scalar(
        select(RecurringRule).where(RecurringRule.id == rule_id, RecurringRule.user_id == user_id)
    )


def add(db: Session, rule: RecurringRule) -> RecurringRule:
    db.add(rule)
    db.flush()
    return rule


def delete(db: Session, rule: RecurringRule) -> None:
    db.delete(rule)
    db.flush()


def lock_due(db: Session, user_id: uuid.UUID, today: date) -> Sequence[RecurringRule]:
    """Active rules with an occurrence due, row-locked so concurrent requests don't both
    generate (SKIP LOCKED: a request that loses the race simply skips those rules)."""
    return db.scalars(
        select(RecurringRule)
        .where(
            RecurringRule.user_id == user_id,
            RecurringRule.is_active,
            RecurringRule.next_run_on <= today,
        )
        .with_for_update(skip_locked=True, of=RecurringRule)
    ).all()


def insert_occurrence(db: Session, rule: RecurringRule, occurred_on: date) -> None:
    """Create the transaction for one occurrence; a no-op if it already exists."""
    db.execute(
        insert(Transaction)
        .values(
            user_id=rule.user_id,
            type=rule.type,
            amount=rule.amount,
            category_id=rule.category_id,
            description=rule.description,
            payment_method=rule.payment_method,
            occurred_on=occurred_on,
            recurring_rule_id=rule.id,
        )
        .on_conflict_do_nothing(
            index_elements=["recurring_rule_id", "occurred_on"],
            index_where=Transaction.recurring_rule_id.is_not(None),
        )
    )
