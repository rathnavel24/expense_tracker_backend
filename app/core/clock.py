from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def today() -> date:
    """Today's calendar date in the app's timezone (not the server's, which may be UTC)."""
    return datetime.now(ZoneInfo(get_settings().app_timezone)).date()
