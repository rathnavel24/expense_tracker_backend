from datetime import date


def month_range(year: int, month: int) -> tuple[date, date]:
    """[first day of month, first day of next month) - an exclusive upper bound."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end
