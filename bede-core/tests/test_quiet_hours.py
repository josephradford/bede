from datetime import datetime
from zoneinfo import ZoneInfo

from bede_core.quiet_hours import is_quiet_hours


TZ = ZoneInfo("Australia/Sydney")


def test_quiet_hours_late_night():
    dt = datetime(2026, 5, 1, 23, 30, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=22, end_hour=7) is True


def test_quiet_hours_early_morning():
    dt = datetime(2026, 5, 1, 5, 0, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=22, end_hour=7) is True


def test_not_quiet_hours_afternoon():
    dt = datetime(2026, 5, 1, 14, 0, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=22, end_hour=7) is False


def test_quiet_hours_boundary_start():
    dt = datetime(2026, 5, 1, 22, 0, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=22, end_hour=7) is True


def test_quiet_hours_boundary_end():
    dt = datetime(2026, 5, 1, 7, 0, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=22, end_hour=7) is False


def test_quiet_hours_disabled():
    dt = datetime(2026, 5, 1, 23, 30, tzinfo=TZ)
    assert is_quiet_hours(dt, start_hour=0, end_hour=0) is False
