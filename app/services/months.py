from datetime import date


def shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_range(year: int, month: int) -> tuple[date, date]:
    """[first day of month, first day of next month) - an exclusive upper bound."""
    next_year, next_month = shift_month(year, month, 1)
    return date(year, month, 1), date(next_year, next_month, 1)
