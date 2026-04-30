from bede_data_mcp.server import (
    get_bede_sessions,
    get_claude_sessions,
    get_podcasts,
    get_safari_history,
    get_screen_time,
    get_youtube_history,
)


async def test_get_screen_time(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "entries": [{"name": "Safari", "seconds": 3420}],
    }
    result = await get_screen_time("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/screen-time", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert len(result["entries"]) == 1


async def test_get_screen_time_with_filters(api):
    api.get.return_value = {"date": "2026-04-30", "entries": []}
    await get_screen_time("2026-04-30", device="iphone", top_n=5)
    api.get.assert_called_once_with(
        "/api/vault/screen-time",
        date="2026-04-30",
        device="iphone",
        top_n=5,
        timezone="Australia/Sydney",
    )


async def test_get_safari_history(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "entries": [{"domain": "github.com", "title": "PR #42"}],
    }
    result = await get_safari_history("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/safari", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["entries"][0]["domain"] == "github.com"


async def test_get_safari_history_with_domain_filter(api):
    api.get.return_value = {"date": "2026-04-30", "entries": []}
    await get_safari_history(
        "2026-04-30", device="mac", domain_filter="github.com", top_n=10
    )
    api.get.assert_called_once_with(
        "/api/vault/safari",
        date="2026-04-30",
        device="mac",
        domain="github.com",
        top_n=10,
        timezone="Australia/Sydney",
    )


async def test_get_youtube_history(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "entries": [{"title": "Tech Talk", "url": "https://youtube.com/watch?v=abc"}],
    }
    result = await get_youtube_history("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/youtube", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert len(result["entries"]) == 1


async def test_get_podcasts(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "entries": [{"podcast": "The Daily", "episode": "Episode 1"}],
    }
    result = await get_podcasts("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/podcasts", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["entries"][0]["podcast"] == "The Daily"


async def test_get_claude_sessions(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "sessions": [{"project": "bede", "duration_min": 45}],
    }
    result = await get_claude_sessions("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/claude-sessions", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["sessions"][0]["project"] == "bede"


async def test_get_bede_sessions(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "sessions": [{"task_name": "morning_briefing", "duration_min": 5}],
    }
    result = await get_bede_sessions("2026-04-30")
    api.get.assert_called_once_with(
        "/api/vault/bede-sessions", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["sessions"][0]["task_name"] == "morning_briefing"
