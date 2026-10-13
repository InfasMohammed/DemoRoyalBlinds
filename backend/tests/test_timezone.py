import os
import subprocess
import sys


def test_dubai_timezone_works_without_system_timezone_files():
    """Windows needs the packaged database; Linux's system files hid this gap."""
    code = '''
from datetime import datetime, timezone
from zoneinfo import TZPATH, ZoneInfo
from app.catalog import today

assert TZPATH == (), "System timezone files must be excluded from this check"
dubai = ZoneInfo("Asia/Dubai")
instant = datetime(2026, 10, 13, 21, 30, tzinfo=timezone.utc).astimezone(dubai)
assert instant.isoformat() == "2026-10-14T01:30:00+04:00"
assert today() == datetime.now(dubai).date()
'''
    subprocess.run([sys.executable, '-c', code],
                   env={**os.environ, 'PYTHONTZPATH': ''},
                   capture_output=True, text=True, check=True)
