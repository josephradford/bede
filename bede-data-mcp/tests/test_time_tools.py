from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from bede_data_mcp.server import calculate_datetime, get_current_time

FROZEN = datetime(2026, 5, 3, 14, 30, 0, tzinfo=ZoneInfo("Australia/Sydney"))


async def test_get_current_time_defaults():
    with patch("bede_data_mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = await get_current_time()

    assert result["date"] == "2026-05-03"
    assert result["time"] == "14:30:00"
    assert result["day_of_week"] == "Sunday"
    assert result["timezone"] == "Australia/Sydney"
    assert result["year"] == 2026
    assert result["month"] == 5
    assert result["day_of_month"] == 3
    assert "unix_timestamp" in result


async def test_get_current_time_utc():
    with patch("bede_data_mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(
            2026, 5, 3, 4, 30, 0, tzinfo=ZoneInfo("UTC")
        )
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = await get_current_time(timezone="UTC")

    assert result["timezone"] == "UTC"
    assert result["utc_offset"] == "+00:00"


async def test_get_current_time_invalid_timezone():
    result = await get_current_time(timezone="Not/A/Timezone")
    assert "error" in result


async def test_calculate_datetime_days_ago():
    with patch("bede_data_mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = await calculate_datetime(days=-3)

    assert result["date"] == "2026-04-30"
    assert result["day_of_week"] == "Thursday"


async def test_calculate_datetime_add_hours():
    with patch("bede_data_mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = await calculate_datetime(hours=5)

    assert result["time"] == "19:30:00"
    assert result["date"] == "2026-05-03"


async def test_calculate_datetime_crosses_midnight():
    with patch("bede_data_mcp.server.datetime") as mock_dt:
        mock_dt.now.return_value = FROZEN
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = await calculate_datetime(hours=12)

    assert result["date"] == "2026-05-04"
    assert result["time"] == "02:30:00"


async def test_calculate_datetime_from_base():
    result = await calculate_datetime(
        days=1, base="2026-01-31T12:00:00", timezone="Australia/Sydney"
    )
    assert result["date"] == "2026-02-01"


async def test_calculate_datetime_base_with_timezone():
    result = await calculate_datetime(
        days=0, base="2026-05-03T04:30:00+00:00", timezone="Australia/Sydney"
    )
    assert result["timezone"] == "Australia/Sydney"
    assert result["date"] == "2026-05-03"
    assert result["time"] == "14:30:00"


async def test_calculate_datetime_invalid_base():
    result = await calculate_datetime(base="not-a-date")
    assert "error" in result


async def test_calculate_datetime_invalid_timezone():
    result = await calculate_datetime(timezone="Fake/Zone")
    assert "error" in result


async def test_calculate_datetime_combined_offsets():
    result = await calculate_datetime(
        days=-1, hours=-2, minutes=-30, base="2026-05-03T14:30:00", timezone="UTC"
    )
    assert result["date"] == "2026-05-02"
    assert result["time"] == "12:00:00"
