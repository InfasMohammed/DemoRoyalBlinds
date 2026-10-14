"""Use the Dubai business date consistently across validation and scheduling."""

from datetime import date, datetime
from zoneinfo import ZoneInfo


def today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()
