from bede_data_mcp.server import acknowledge_flag, get_analytics_flags


async def test_get_analytics_flags(api):
    api.get.return_value = {
        "flags": [{"id": 1, "signal": "sleep_declining", "severity": "concern"}]
    }
    result = await get_analytics_flags()
    api.get.assert_called_once_with("/api/analytics/flags")
    assert result["flags"][0]["signal"] == "sleep_declining"


async def test_get_analytics_flags_with_filters(api):
    api.get.return_value = {"flags": []}
    await get_analytics_flags(severity="alert", acknowledged=False, limit=10)
    api.get.assert_called_once_with(
        "/api/analytics/flags", severity="alert", acknowledged=False, limit=10
    )


async def test_acknowledge_flag(api):
    api.put.return_value = {"id": 1, "signal": "sleep_declining", "acknowledged": True}
    result = await acknowledge_flag(1)
    api.put.assert_called_once_with("/api/analytics/flags/1/acknowledge")
    assert result["acknowledged"] is True
