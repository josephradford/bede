from unittest.mock import AsyncMock, patch

from bede_data.live.location import OwnTracksNotConfiguredError


def test_location_summary_returns_503_when_not_configured(client):
    with patch(
        "bede_data.api.location.fetch_owntracks_points",
        new_callable=AsyncMock,
        side_effect=OwnTracksNotConfiguredError(
            "OWNTRACKS_USER and OWNTRACKS_DEVICE must be set"
        ),
    ):
        response = client.get("/api/location/summary", params={"date": "2026-04-30"})
    assert response.status_code == 503
    assert "OWNTRACKS_USER" in response.json()["error"]


def test_location_raw_returns_503_when_not_configured(client):
    with patch(
        "bede_data.api.location.fetch_owntracks_points",
        new_callable=AsyncMock,
        side_effect=OwnTracksNotConfiguredError(
            "OWNTRACKS_USER and OWNTRACKS_DEVICE must be set"
        ),
    ):
        response = client.get(
            "/api/location/raw",
            params={"from_date": "2026-04-30", "to_date": "2026-04-30"},
        )
    assert response.status_code == 503
    assert "OWNTRACKS_USER" in response.json()["error"]
