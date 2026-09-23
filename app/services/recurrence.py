"""Monthly recurrence arithmetic. Pure functions, no I/O."""

import calendar
from datetime import date

from app.services.months import shift_month as _shift_month


def occurrence_in(year: int, month: int, day_of_month: int) -> date:
    """The rule's date in a given month, clamped to the month's length (31 -> 30 Sep)."""
    return date(year, month, min(day_of_month, calendar.monthrange(year, month)[1]))


def next_occurrence_after(after: date, day_of_month: int) -> date:
    """First occurrence strictly after `after`."""
    candidate = occurrence_in(after.year, after.month, day_of_month)
    if candidate > after:
        return candidate
    return occurrence_in(*_shift_month(after.year, after.month, 1), day_of_month)


def occurrence_in_month_after(d: date, day_of_month: int) -> date:
    """The occurrence in the calendar month following `d`'s month."""
    return occurrence_in(*_shift_month(d.year, d.month, 1), day_of_month)


def first_occurrence_on_or_after(on_or_after: date, day_of_month: int) -> date:
    candidate = occurrence_in(on_or_after.year, on_or_after.month, day_of_month)
    if candidate >= on_or_after:
        return candidate
    return occurrence_in(*_shift_month(on_or_after.year, on_or_after.month, 1), day_of_month)
