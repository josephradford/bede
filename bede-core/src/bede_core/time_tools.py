import calendar
from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_UNITS = ("days", "weeks", "months", "years")
_WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def _fmt(d: date) -> str:
    return f"{d:%A}, {d.day} {d:%B %Y} ({d.isoformat()})"


def _add_months(d: date, months: int) -> date:
    """Add whole months, clamping to the last day (31 Jan + 1 month = 28/29 Feb)."""
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_time_tools(
    timezone: str = "Australia/Sydney",
    today: Callable[[], date] | None = None,
) -> list[Callable]:
    """Deterministic date arithmetic for the agent, so it never does it in its head.

    Errors come back as text so the model can recover.
    """
    tz = ZoneInfo(timezone)

    def _today() -> date:
        return today() if today else datetime.now(tz).date()

    def _parse(value: str) -> date:
        if value.strip().lower() == "today":
            return _today()
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            raise ValueError(f"'{value}' is not 'today' or a YYYY-MM-DD date") from None

    def calculate_date(
        offset: int, unit: str = "days", from_date: str = "today"
    ) -> str:
        """Add (or, if negative, subtract) days, weeks, months or years to a date.

        from_date is 'today' or YYYY-MM-DD. Returns the weekday and date. Use this
        for every relative date ("in 3 days", "two weeks ago", "a month from now").
        """
        try:
            start = _parse(from_date)
            unit = unit.strip().lower()
            if unit not in _UNITS:
                raise ValueError(f"unit must be one of {', '.join(_UNITS)}")
            if unit == "days":
                result = start + timedelta(days=offset)
            elif unit == "weeks":
                result = start + timedelta(weeks=offset)
            elif unit == "months":
                result = _add_months(start, offset)
            else:
                result = _add_months(start, offset * 12)
            return _fmt(result)
        except (ValueError, OverflowError) as e:
            return f"Error: {e}"

    def days_between(start: str, end: str = "today") -> str:
        """Number of days from start to end (negative if end is earlier).

        Both are 'today' or YYYY-MM-DD.
        """
        try:
            n = (_parse(end) - _parse(start)).days
        except ValueError as e:
            return f"Error: {e}"
        return f"{n} {'day' if abs(n) == 1 else 'days'}"

    def find_weekday(
        weekday: str, which: str = "next", from_date: str = "today"
    ) -> str:
        """Find the next or last given weekday strictly after or before a date.

        weekday is a name or 3-letter abbreviation (e.g. 'tuesday', 'fri'); which is
        'next' or 'last'. If from_date is already that weekday, the result is a week
        away. Use for "next Friday" or "last Tuesday".
        """
        try:
            start = _parse(from_date)
            name = weekday.strip().lower()
            matches = [i for i, w in enumerate(_WEEKDAYS) if w.startswith(name[:3])]
            if len(name) < 3 or len(matches) != 1:
                raise ValueError(f"'{weekday}' is not a weekday name")
            which = which.strip().lower()
            if which not in ("next", "last"):
                raise ValueError("which must be 'next' or 'last'")
            target = matches[0]
            if which == "next":
                delta = (target - start.weekday()) % 7 or 7
            else:
                delta = -((start.weekday() - target) % 7 or 7)
            return _fmt(start + timedelta(days=delta))
        except (ValueError, OverflowError) as e:
            return f"Error: {e}"

    return [calculate_date, days_between, find_weekday]
