import json
import re
from datetime import datetime, timezone

_MEDICATION_RE = re.compile(r"medication", re.IGNORECASE)

_TS_PATTERNS = [
    r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) ([+-]\d{4})",
    r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})",
]


def _parse_timestamp(ts_str: str) -> tuple[str, str] | None:
    """Parse HAE timestamp to (local_date, utc_iso8601). HAE sends timestamps
    as 'YYYY-MM-DD HH:MM:SS +HHMM' (local with offset)."""
    if not ts_str:
        return None
    for pattern in _TS_PATTERNS:
        m = re.match(pattern, ts_str.strip())
        if m:
            date_part, time_part, offset = m.groups()
            if ":" not in offset:
                offset = offset[:3] + ":" + offset[3:]
            iso_str = f"{date_part}T{time_part}{offset}"
            try:
                dt = datetime.fromisoformat(iso_str)
                local_date = dt.strftime("%Y-%m-%d")
                utc_iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                return local_date, utc_iso
            except ValueError:
                continue
    try:
        dt = datetime.fromisoformat(ts_str.strip())
        local_date = dt.strftime("%Y-%m-%d")
        utc_iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return local_date, utc_iso
    except ValueError:
        return None


def _parse_date(date_str: str) -> str:
    parsed = _parse_timestamp(date_str)
    if parsed:
        return parsed[0]
    return date_str[:10] if len(date_str) >= 10 else date_str


def _parse_datetime(date_str: str) -> str:
    parsed = _parse_timestamp(date_str)
    if parsed:
        return parsed[1]
    return date_str


def _hours_between(start_str: str, end_str: str) -> float:
    s = _parse_timestamp(start_str)
    e = _parse_timestamp(end_str)
    if s and e:
        try:
            start = datetime.fromisoformat(s[1].replace("Z", "+00:00"))
            end = datetime.fromisoformat(e[1].replace("Z", "+00:00"))
            return (end - start).total_seconds() / 3600
        except ValueError:
            pass
    return 0.0


def _extract_qty(value) -> float | None:
    """Extract qty from a field that may be a dict, list of dicts, or a scalar."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return value.get("qty")
    if isinstance(value, list) and value:
        return value[0].get("qty") if isinstance(value[0], dict) else None
    return None


def _extract_named_stages(analysis: dict, date: str, source: str) -> list[dict]:
    """Extract named sleep stage fields (core, deep, rem, etc.) from an analysis entry."""
    rows = []
    start_ts = _parse_timestamp(
        analysis.get("sleepStart", "") or analysis.get("startDate", "")
    )
    end_ts = _parse_timestamp(
        analysis.get("sleepEnd", "") or analysis.get("endDate", "")
    )
    start_utc = start_ts[1] if start_ts else None
    end_utc = end_ts[1] if end_ts else None

    for stage in ("core", "deep", "rem", "awake", "inBed", "asleep"):
        val = analysis.get(stage)
        if val is not None and val != 0:
            try:
                rows.append(
                    {
                        "date": date,
                        "phase": stage,
                        "hours": float(val),
                        "start_time": start_utc,
                        "end_time": end_utc,
                        "source": source or None,
                    }
                )
            except (ValueError, TypeError):
                pass
    return rows


def _process_sleep(metric: dict) -> list[dict]:
    """Process sleep data from all HAE formats: aggregatedSleepAnalyses,
    sleepAnalyses, data[] as analyses (named stage fields), and
    data[].sleepAnalysis (inline HK phase entries)."""
    rows = []

    # Format 1: top-level aggregated or non-aggregated analyses
    analyses = metric.get("aggregatedSleepAnalyses", [])
    if not analyses:
        analyses = metric.get("sleepAnalyses", [])

    for analysis in analyses:
        end_ts = _parse_timestamp(
            analysis.get("sleepEnd", "") or analysis.get("endDate", "")
        )
        start_ts = _parse_timestamp(
            analysis.get("sleepStart", "") or analysis.get("startDate", "")
        )
        date = end_ts[0] if end_ts else (start_ts[0] if start_ts else None)
        if not date:
            continue
        source = analysis.get("source") or analysis.get("sleepSource", "")
        rows.extend(_extract_named_stages(analysis, date, source))

    # Format 2: data[] entries
    for entry in metric.get("data", []):
        date = _parse_date(entry.get("date", ""))
        source = entry.get("source", "")

        # 2a: entries with sleepAnalysis sub-arrays (summarised inline HK phases)
        for phase_entry in entry.get("sleepAnalysis", []):
            phase = phase_entry.get("value", "")
            prefix = "HKCategoryValueSleepAnalysis."
            if phase.startswith(prefix):
                phase = phase[len(prefix) :]

            hours = _hours_between(
                phase_entry.get("startDate", ""), phase_entry.get("endDate", "")
            )
            rows.append(
                {
                    "date": date,
                    "phase": phase,
                    "hours": hours,
                    "start_time": _parse_datetime(phase_entry.get("startDate", "")),
                    "end_time": _parse_datetime(phase_entry.get("endDate", "")),
                    "source": source or None,
                }
            )

        # 2b: entries that ARE phase records (unsummarised — value/qty/startDate/endDate)
        phase_value = entry.get("value", "")
        if phase_value and entry.get("startDate"):
            prefix = "HKCategoryValueSleepAnalysis."
            if phase_value.startswith(prefix):
                phase_value = phase_value[len(prefix) :]
            hours = entry.get("qty")
            if hours is None:
                hours = _hours_between(
                    entry.get("startDate", ""), entry.get("endDate", "")
                )
            else:
                hours = float(hours)
            rows.append(
                {
                    "date": date,
                    "phase": phase_value,
                    "hours": hours,
                    "start_time": _parse_datetime(entry.get("startDate", "")),
                    "end_time": _parse_datetime(entry.get("endDate", "")),
                    "source": source or None,
                }
            )

        # 2c: entries with named stage fields (e.g. core, deep, rem as keys)
        if not analyses:
            rows.extend(_extract_named_stages(entry, date, source))

    return rows


def _process_state_of_mind(entries: list) -> list[dict]:
    """Process data.stateOfMind top-level array from HAE."""
    rows = []
    for entry in entries:
        parsed = _parse_timestamp(entry.get("start", ""))
        if not parsed:
            continue
        date, utc_iso = parsed
        labels = entry.get("labels")
        if isinstance(labels, list):
            labels = json.dumps(labels) if labels else None
        associations = entry.get("associations")
        if isinstance(associations, list):
            associations = json.dumps(associations) if associations else None
        context = entry.get("context")
        if isinstance(context, list):
            context = json.dumps(context) if context else None
        rows.append(
            {
                "date": date,
                "valence": entry.get("valence"),
                "labels": labels,
                "context": context,
                "associations": associations,
                "recorded_at": utc_iso,
            }
        )
    return rows


def parse_health_payload(payload: dict) -> dict:
    """Parse an Apple Health Export JSON payload into table-ready row dicts.
    Handles all HAE formats: aggregated sleep, inline sleep phases,
    top-level stateOfMind, regex-matched medications, and list-typed
    workout fields."""
    result = {
        "health_metrics": [],
        "sleep_phases": [],
        "workouts": [],
        "medications": [],
        "state_of_mind": [],
    }

    data = payload.get("data", {})

    for metric in data.get("metrics", []):
        name = metric.get("name", "")
        units = metric.get("units", "")

        if (
            name == "sleep_analysis"
            or metric.get("aggregatedSleepAnalyses")
            or metric.get("sleepAnalyses")
        ):
            result["sleep_phases"].extend(_process_sleep(metric))
        elif _MEDICATION_RE.search(name):
            for entry in metric.get("data", []):
                date = _parse_date(entry.get("date", ""))
                result["medications"].append(
                    {
                        "date": date,
                        "medication": name,
                        "quantity": entry.get("qty"),
                        "unit": units or None,
                        "recorded_at": _parse_datetime(entry.get("date", "")),
                    }
                )
        else:
            for entry in metric.get("data", []):
                date = _parse_date(entry.get("date", ""))
                source = entry.get("source", "")
                qty = entry.get("qty")
                if qty is None:
                    qty = entry.get("Avg")
                if qty is None:
                    continue
                try:
                    value = float(qty)
                except (ValueError, TypeError):
                    continue
                result["health_metrics"].append(
                    {
                        "date": date,
                        "metric": name,
                        "value": value,
                        "source": source or None,
                        "recorded_at": _parse_datetime(entry.get("date", "")),
                    }
                )

    for workout in data.get("workouts", []):
        start_str = workout.get("start", "")
        end_str = workout.get("end", "")
        duration = _hours_between(start_str, end_str) * 60
        result["workouts"].append(
            {
                "date": _parse_date(start_str),
                "workout_type": workout.get("name", ""),
                "duration_minutes": round(duration, 1),
                "active_energy_kj": _extract_qty(
                    workout.get("activeEnergy") or workout.get("activeEnergyBurned")
                ),
                "avg_heart_rate": _extract_qty(workout.get("avgHeartRate")),
                "max_heart_rate": _extract_qty(workout.get("maxHeartRate")),
                "start_time": _parse_datetime(start_str),
            }
        )

    result["state_of_mind"].extend(_process_state_of_mind(data.get("stateOfMind", [])))

    return result
