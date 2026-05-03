from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def utc_to_local(ts: str | None, tz: str) -> str | None:
    """Convert a UTC timestamp string to local time in the given timezone."""
    if not ts:
        return ts
    try:
        normalized = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(ZoneInfo(tz))
        return local.strftime("%Y-%m-%dT%H:%M:%S")
    except (ValueError, KeyError):
        return ts
