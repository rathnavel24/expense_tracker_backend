"""Small pure helpers shared across services: calendar maths, "today", pagination cursors."""

import base64
import binascii
import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.core.errors import ValidationFailedError

# --- Today ---------------------------------------------------------------------------------


def today() -> date:
    """Today's calendar date in the app's timezone (not the server's, which may be UTC)."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()


# --- Months --------------------------------------------------------------------------------


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_range(year: int, month: int) -> tuple[date, date]:
    """[first day of month, first day of next month) - an exclusive upper bound."""
    next_year, next_month = shift_month(year, month, 1)
    return date(year, month, 1), date(next_year, next_month, 1)


# --- Monthly recurrence --------------------------------------------------------------------


def occurrence_in(year: int, month: int, day_of_month: int) -> date:
    """A rule's date in a given month, clamped to the month's length (31 -> 30 Sep)."""
    return date(year, month, min(day_of_month, calendar.monthrange(year, month)[1]))


def next_occurrence_after(after: date, day_of_month: int) -> date:
    """First occurrence strictly after `after`."""
    candidate = occurrence_in(after.year, after.month, day_of_month)
    if candidate > after:
        return candidate
    return occurrence_in(*shift_month(after.year, after.month, 1), day_of_month)


def occurrence_in_month_after(d: date, day_of_month: int) -> date:
    """The occurrence in the calendar month following `d`'s month."""
    return occurrence_in(*shift_month(d.year, d.month, 1), day_of_month)


def first_occurrence_on_or_after(on_or_after: date, day_of_month: int) -> date:
    candidate = occurrence_in(on_or_after.year, on_or_after.month, day_of_month)
    if candidate >= on_or_after:
        return candidate
    return occurrence_in(*shift_month(on_or_after.year, on_or_after.month, 1), day_of_month)


# --- Keyset pagination cursors -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cursor:
    """Keyset position: the sort key of the last item on the previous page."""

    occurred_on: date
    created_at: datetime
    id: uuid.UUID


def encode_cursor(occurred_on: date, created_at: datetime, id_: uuid.UUID) -> str:
    raw = f"{occurred_on.isoformat()}|{created_at.isoformat()}|{id_}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(value: str) -> Cursor:
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
