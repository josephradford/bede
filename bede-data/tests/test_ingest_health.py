from bede_data.config import settings
from bede_data.ingest.health_parser import parse_health_payload


def test_ingest_health_rejects_missing_token(client):
    response = client.post("/ingest/health", json={})
    assert response.status_code == 401


def test_ingest_health_rejects_bad_token(client):
    settings.ingest_write_token = "correct-token"
    response = client.post(
        "/ingest/health",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_ingest_health_accepts_valid_token(client):
    settings.ingest_write_token = "correct-token"
    response = client.post(
        "/ingest/health",
        json={"data": {"metrics": []}},
        headers={"Authorization": "Bearer correct-token"},
    )
    assert response.status_code == 200


def test_parse_basic_metrics():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "data": [
                        {
                            "date": "2026-04-29 00:00:00 +1000",
                            "qty": 8500,
                            "source": "iPhone",
                        }
                    ],
                },
                {
                    "name": "active_energy",
                    "data": [
                        {
                            "date": "2026-04-29 00:00:00 +1000",
                            "qty": 2100.5,
                            "source": "Apple Watch",
                        }
                    ],
                },
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["health_metrics"]) == 2
    assert result["health_metrics"][0]["metric"] == "step_count"
    assert result["health_metrics"][0]["value"] == 8500
    assert result["health_metrics"][0]["date"] == "2026-04-29"
    assert result["health_metrics"][0]["source"] == "iPhone"


def test_parse_sleep_inline_phases():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "data": [
                        {
                            "date": "2026-04-29 00:00:00 +1000",
                            "source": "Apple Watch",
                            "sleepAnalysis": [
                                {
                                    "value": "HKCategoryValueSleepAnalysis.asleepCore",
                                    "startDate": "2026-04-28 23:00:00 +1000",
                                    "endDate": "2026-04-29 01:30:00 +1000",
                                },
                                {
                                    "value": "HKCategoryValueSleepAnalysis.asleepDeep",
                                    "startDate": "2026-04-29 01:30:00 +1000",
                                    "endDate": "2026-04-29 03:00:00 +1000",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["sleep_phases"]) == 2
    assert result["sleep_phases"][0]["phase"] == "asleepCore"
    assert result["sleep_phases"][0]["hours"] == 2.5
    assert result["sleep_phases"][1]["phase"] == "asleepDeep"
    assert result["sleep_phases"][1]["hours"] == 1.5


def test_parse_sleep_aggregated():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "aggregatedSleepAnalyses": [
                        {
                            "sleepStart": "2026-04-28 23:00:00 +1000",
                            "sleepEnd": "2026-04-29 07:00:00 +1000",
                            "source": "Apple Watch",
                            "core": 3.5,
                            "deep": 1.2,
                            "rem": 1.8,
                            "awake": 0.5,
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    phases = {p["phase"]: p["hours"] for p in result["sleep_phases"]}
    assert phases["core"] == 3.5
    assert phases["deep"] == 1.2
    assert phases["rem"] == 1.8
    assert phases["awake"] == 0.5
    assert result["sleep_phases"][0]["date"] == "2026-04-29"


def test_parse_sleep_data_entries_as_analyses():
    """When no aggregatedSleepAnalyses or sleepAnalyses exist, data[] entries
    themselves may contain named stage fields."""
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "data": [
                        {
                            "date": "2026-04-29 07:00:00 +1000",
                            "source": "Apple Watch",
                            "sleepStart": "2026-04-28 23:00:00 +1000",
                            "sleepEnd": "2026-04-29 07:00:00 +1000",
                            "core": 3.0,
                            "deep": 1.5,
                            "rem": 2.0,
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    phases = {p["phase"]: p["hours"] for p in result["sleep_phases"]}
    assert phases["core"] == 3.0
    assert phases["deep"] == 1.5
    assert phases["rem"] == 2.0


def test_parse_workouts_dict_fields():
    payload = {
        "data": {
            "workouts": [
                {
                    "name": "Running",
                    "start": "2026-04-29 07:00:00 +1000",
                    "end": "2026-04-29 07:45:00 +1000",
                    "activeEnergy": {"qty": 1800, "units": "kJ"},
                    "avgHeartRate": {"qty": 155, "units": "bpm"},
                    "maxHeartRate": {"qty": 178, "units": "bpm"},
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["workouts"]) == 1
    assert result["workouts"][0]["workout_type"] == "Running"
    assert result["workouts"][0]["duration_minutes"] == 45.0
    assert result["workouts"][0]["active_energy_kj"] == 1800


def test_parse_workouts_list_fields():
    payload = {
        "data": {
            "workouts": [
                {
                    "name": "Walking",
                    "start": "2026-04-29 08:00:00 +1000",
                    "end": "2026-04-29 08:30:00 +1000",
                    "activeEnergy": [{"qty": 500, "units": "kJ"}],
                    "avgHeartRate": [{"qty": 110, "units": "bpm"}],
                    "maxHeartRate": [{"qty": 130, "units": "bpm"}],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert result["workouts"][0]["active_energy_kj"] == 500
    assert result["workouts"][0]["avg_heart_rate"] == 110


def test_parse_workouts_scalar_fields():
    payload = {
        "data": {
            "workouts": [
                {
                    "name": "Yoga",
                    "start": "2026-04-29 09:00:00 +1000",
                    "end": "2026-04-29 10:00:00 +1000",
                    "activeEnergy": 400.0,
                    "avgHeartRate": 90,
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert result["workouts"][0]["active_energy_kj"] == 400.0
    assert result["workouts"][0]["avg_heart_rate"] == 90


def test_parse_medications_regex():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "Medication_Lexapro",
                    "units": "tablet",
                    "data": [
                        {
                            "date": "2026-04-29 08:00:00 +1000",
                            "qty": 1,
                            "source": "Health",
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["medications"]) == 1
    assert result["medications"][0]["medication"] == "Medication_Lexapro"
    assert result["medications"][0]["quantity"] == 1
    assert result["medications"][0]["unit"] == "tablet"


def test_parse_state_of_mind_top_level():
    """stateOfMind is a top-level array in data, not inside metrics."""
    payload = {
        "data": {
            "stateOfMind": [
                {
                    "start": "2026-04-29 14:00:00 +1000",
                    "end": "2026-04-29 14:00:00 +1000",
                    "kind": "mood",
                    "valence": 0.7,
                    "labels": ["Happy", "Calm"],
                    "associations": ["Work"],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["state_of_mind"]) == 1
    assert result["state_of_mind"][0]["valence"] == 0.7
    assert result["state_of_mind"][0]["date"] == "2026-04-29"
    import json

    assert json.loads(result["state_of_mind"][0]["labels"]) == ["Happy", "Calm"]
    assert json.loads(result["state_of_mind"][0]["associations"]) == ["Work"]


def test_parse_skips_metrics_with_no_qty():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "data": [{"date": "2026-04-29 00:00:00 +1000", "source": "iPhone"}],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert result["health_metrics"] == []


def test_ingest_health_stores_metrics(client, db):
    settings.ingest_write_token = "test-token"
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "data": [
                        {
                            "date": "2026-04-29 00:00:00 +1000",
                            "qty": 8500,
                            "source": "iPhone",
                        }
                    ],
                }
            ]
        }
    }
    response = client.post(
        "/ingest/health",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["records"] > 0

    cursor = db.execute("SELECT * FROM health_metrics WHERE date = '2026-04-29'")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["metric"] == "step_count"
    assert rows[0]["value"] == 8500


def test_ingest_health_upserts_on_duplicate(client, db):
    settings.ingest_write_token = "test-token"
    headers = {"Authorization": "Bearer test-token"}
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "step_count",
                    "data": [
                        {
                            "date": "2026-04-29 00:00:00 +1000",
                            "qty": 8500,
                            "source": "iPhone",
                        }
                    ],
                }
            ]
        }
    }
    client.post("/ingest/health", json=payload, headers=headers)

    payload["data"]["metrics"][0]["data"][0]["qty"] = 9500
    response = client.post("/ingest/health", json=payload, headers=headers)
    assert response.status_code == 200

    cursor = db.execute("SELECT * FROM health_metrics WHERE date = '2026-04-29'")
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 9500


def test_parse_metric_avg_fallback():
    """Unsummarised metrics (e.g. heart_rate) use Avg/Min/Max instead of qty."""
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "heart_rate",
                    "units": "bpm",
                    "data": [
                        {
                            "date": "2026-04-29 08:30:00 +1000",
                            "Avg": 72,
                            "Min": 60,
                            "Max": 85,
                            "source": "Apple Watch",
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["health_metrics"]) == 1
    assert result["health_metrics"][0]["metric"] == "heart_rate"
    assert result["health_metrics"][0]["value"] == 72
    assert result["health_metrics"][0]["source"] == "Apple Watch"


def test_parse_sleep_unsummarised_phase_records():
    """Unsummarised sleep: data[] entries that ARE phase records with value/qty."""
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "data": [
                        {
                            "date": "2026-04-29 07:00:00 +1000",
                            "value": "HKCategoryValueSleepAnalysis.asleepCore",
                            "qty": 3.2,
                            "startDate": "2026-04-28 23:00:00 +1000",
                            "endDate": "2026-04-29 02:12:00 +1000",
                            "source": "Apple Watch",
                        },
                        {
                            "date": "2026-04-29 07:00:00 +1000",
                            "value": "HKCategoryValueSleepAnalysis.asleepDeep",
                            "qty": 1.5,
                            "startDate": "2026-04-29 02:12:00 +1000",
                            "endDate": "2026-04-29 03:42:00 +1000",
                            "source": "Apple Watch",
                        },
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    phases = {p["phase"]: p for p in result["sleep_phases"]}
    assert "asleepCore" in phases
    assert phases["asleepCore"]["hours"] == 3.2
    assert "asleepDeep" in phases
    assert phases["asleepDeep"]["hours"] == 1.5


def test_parse_sleep_unsummarised_no_qty_uses_duration():
    """Unsummarised sleep without qty falls back to calculating hours from start/end."""
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "data": [
                        {
                            "date": "2026-04-29 07:00:00 +1000",
                            "value": "HKCategoryValueSleepAnalysis.asleepREM",
                            "startDate": "2026-04-29 03:00:00 +1000",
                            "endDate": "2026-04-29 05:00:00 +1000",
                            "source": "Apple Watch",
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["sleep_phases"]) == 1
    assert result["sleep_phases"][0]["phase"] == "asleepREM"
    assert result["sleep_phases"][0]["hours"] == 2.0
