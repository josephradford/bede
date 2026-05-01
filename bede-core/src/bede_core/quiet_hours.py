from datetime import datetime


def is_quiet_hours(now: datetime, start_hour: int, end_hour: int) -> bool:
    """Check if the current time falls within quiet hours.

    Quiet hours span midnight: e.g., start=22, end=7 means 22:00-06:59.
    Returns False if start == end == 0 (disabled).
    """
    if start_hour == 0 and end_hour == 0:
        return False
    hour = now.hour
    if start_hour > end_hour:
        return hour >= start_hour or hour < end_hour
    return start_hour <= hour < end_hour
