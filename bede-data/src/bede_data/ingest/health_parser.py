from datetime import datetime


def _parse_date(date_str: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str[:10]


def _parse_datetime(date_str: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return date_str


def _parse_sleep_phase(value: str) -> str:
    """Strip Apple Health's HKCategoryValueSleepAnalysis prefix to get just the phase name (e.g. 'inBed', 'asleep')."""
    prefix = "HKCategoryValueSleepAnalysis."
    if value.startswith(prefix):
        return value[len(prefix) :]
    return value


def _hours_between(start_str: str, end_str: str) -> float:
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            start = datetime.strptime(start_str, fmt)
            end = datetime.strptime(end_str, fmt)
            return (end - start).total_seconds() / 3600
        except ValueError:
            continue
    return 0.0


def _extract_qty(value) -> float | None:
    """Extract qty from a Health Export field that may be a dict, a list of dicts, or None."""
    if isinstance(value, dict):
        return value.get("qty")
    if isinstance(value, list) and value:
        return value[0].get("qty")
    return None


SPECIAL_METRICS = {"sleep_analysis", "medication_record", "state_of_mind"}


def parse_health_payload(payload: dict) -> dict:
    """Parse an Apple Health Export JSON payload into table-ready row dicts. Special metrics (sleep, medications, state of mind) are routed to dedicated tables; everything else goes to health_metrics as a generic name/value pair."""
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

        for entry in metric.get("data", []):
            date = _parse_date(entry.get("date", ""))
            source = entry.get("source", "")

            if name == "sleep_analysis":
                for phase_entry in entry.get("sleepAnalysis", []):
                    phase = _parse_sleep_phase(phase_entry.get("value", ""))
                    hours = _hours_between(
                        phase_entry.get("startDate", ""),
                        phase_entry.get("endDate", ""),
                    )
                    result["sleep_phases"].append(
                        {
                            "date": date,
                            "phase": phase,
                            "hours": hours,
                            "start_time": _parse_datetime(
                                phase_entry.get("startDate", "")
                            ),
                            "end_time": _parse_datetime(phase_entry.get("endDate", "")),
                            "source": source,
                        }
                    )
            elif name == "medication_record":
                result["medications"].append(
                    {
                        "date": date,
                        "medication": entry.get("medication", ""),
                        "quantity": entry.get("qty"),
                        "unit": entry.get("unit"),
                        "recorded_at": _parse_datetime(entry.get("date", "")),
                    }
                )
            elif name == "state_of_mind":
                result["state_of_mind"].append(
                    {
                        "date": date,
                        "valence": entry.get("valence"),
                        "labels": entry.get("labels"),
                        "context": entry.get("context"),
                        "associations": entry.get("associations"),
                        "recorded_at": _parse_datetime(entry.get("date", "")),
                    }
                )
            else:
                result["health_metrics"].append(
                    {
                        "date": date,
                        "metric": name,
                        "value": entry.get("qty", 0),
                        "source": source,
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
                "active_energy_kj": _extract_qty(workout.get("activeEnergy")),
                "avg_heart_rate": _extract_qty(workout.get("avgHeartRate")),
                "max_heart_rate": _extract_qty(workout.get("maxHeartRate")),
                "start_time": _parse_datetime(start_str),
            }
        )

    return result
