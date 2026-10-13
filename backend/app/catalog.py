"""Clock utility. Business records are loaded through business_data.py."""
from datetime import datetime
from zoneinfo import ZoneInfo


def today():
    return datetime.now(ZoneInfo('Asia/Dubai')).date()
