def test_get_analytics_flags_empty(client):
    response = client.get("/api/analytics/flags")
    assert response.status_code == 200
    assert response.json()["flags"] == []


def test_run_analytics_and_get_flags(client, db):
    db.execute("INSERT INTO sleep_phases (date, phase, hours, source) VALUES ('2026-04-27', 'total', 4.0, 'test')")
    db.execute("INSERT INTO sleep_phases (date, phase, hours, source) VALUES ('2026-04-28', 'total', 5.0, 'test')")
    db.execute("INSERT INTO sleep_phases (date, phase, hours, source) VALUES ('2026-04-29', 'total', 4.5, 'test')")
    db.commit()

    response = client.post("/api/analytics/run")
    assert response.status_code == 200
    assert response.json()["flags_stored"] > 0

    response = client.get("/api/analytics/flags")
    flags = response.json()["flags"]
    assert any(f["signal"] == "sleep_declining" for f in flags)


def test_get_flags_filter_severity(client, db):
    db.execute("INSERT INTO analytics_flags (signal, severity, detail, data, computed_at) VALUES ('test_info', 'info', 'test', '{}', '2026-04-29T00:00:00Z')")
    db.execute("INSERT INTO analytics_flags (signal, severity, detail, data, computed_at) VALUES ('test_alert', 'alert', 'test', '{}', '2026-04-29T00:00:00Z')")
    db.commit()

    response = client.get("/api/analytics/flags", params={"severity": "alert"})
    flags = response.json()["flags"]
    assert len(flags) == 1
    assert flags[0]["severity"] == "alert"


def test_acknowledge_flag(client, db):
    db.execute("INSERT INTO analytics_flags (signal, severity, detail, data, computed_at) VALUES ('test', 'info', 'test', '{}', '2026-04-29T00:00:00Z')")
    db.commit()
    flag_id = db.execute("SELECT id FROM analytics_flags").fetchone()["id"]

    response = client.put(f"/api/analytics/flags/{flag_id}/acknowledge")
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True
