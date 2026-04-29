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


def test_parse_sleep_analysis():
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


def test_parse_workouts():
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


def test_parse_medications():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "medication_record",
                    "data": [
                        {
                            "date": "2026-04-29 08:00:00 +1000",
                            "medication": "Lexapro",
                            "qty": 1,
                            "unit": "tablet",
                            "source": "Health",
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["medications"]) == 1
    assert result["medications"][0]["medication"] == "Lexapro"
    assert result["medications"][0]["quantity"] == 1


def test_parse_state_of_mind():
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "state_of_mind",
                    "data": [
                        {
                            "date": "2026-04-29 14:00:00 +1000",
                            "valence": 0.7,
                            "labels": "Happy,Calm",
                            "context": "Work",
                            "associations": "Productivity",
                            "source": "Health",
                        }
                    ],
                }
            ]
        }
    }
    result = parse_health_payload(payload)
    assert len(result["state_of_mind"]) == 1
    assert result["state_of_mind"][0]["valence"] == 0.7
    assert result["state_of_mind"][0]["labels"] == "Happy,Calm"


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
