from bede_data_mcp.server import (
    create_monitored_item,
    create_schedule,
    delete_monitored_item,
    get_setting,
    list_monitored_items,
    list_schedules,
    list_settings,
    set_setting,
    update_schedule,
)


# --- Schedules ---


async def test_list_schedules(api):
    api.get.return_value = {"schedules": [{"id": 1, "task_name": "morning_briefing"}]}
    result = await list_schedules()
    api.get.assert_called_once_with("/api/config/schedules")
    assert len(result["schedules"]) == 1


async def test_create_schedule(api):
    api.post.return_value = {
        "id": 1,
        "task_name": "morning_briefing",
        "cron_expression": "0 8 * * 1-5",
    }
    result = await create_schedule(
        "morning_briefing", "0 8 * * 1-5", "Deliver the morning briefing"
    )
    api.post.assert_called_once_with(
        "/api/config/schedules",
        {
            "task_name": "morning_briefing",
            "cron_expression": "0 8 * * 1-5",
            "prompt": "Deliver the morning briefing",
        },
    )
    assert result["task_name"] == "morning_briefing"


async def test_create_schedule_with_options(api):
    api.post.return_value = {"id": 2, "task_name": "reflection"}
    await create_schedule(
        "reflection",
        "0 21 * * *",
        "Evening reflection",
        model="opus",
        timeout_seconds=600,
        interactive=True,
        enabled=True,
    )
    api.post.assert_called_once_with(
        "/api/config/schedules",
        {
            "task_name": "reflection",
            "cron_expression": "0 21 * * *",
            "prompt": "Evening reflection",
            "model": "opus",
            "timeout_seconds": 600,
            "interactive": True,
            "enabled": True,
        },
    )


async def test_update_schedule(api):
    api.put.return_value = {"id": 1, "cron_expression": "0 7 * * 1-5"}
    result = await update_schedule(1, cron_expression="0 7 * * 1-5")
    api.put.assert_called_once_with(
        "/api/config/schedules/1", {"cron_expression": "0 7 * * 1-5"}
    )
    assert result["cron_expression"] == "0 7 * * 1-5"


async def test_update_schedule_enabled(api):
    api.put.return_value = {"id": 1, "enabled": False}
    await update_schedule(1, enabled=False)
    api.put.assert_called_once_with("/api/config/schedules/1", {"enabled": False})


# --- Settings ---


async def test_list_settings(api):
    api.get.return_value = {
        "settings": [{"key": "quiet_hours_start", "value": "22:00"}]
    }
    result = await list_settings()
    api.get.assert_called_once_with("/api/config/settings")
    assert len(result["settings"]) == 1


async def test_get_setting(api):
    api.get.return_value = {"key": "quiet_hours_start", "value": "22:00"}
    result = await get_setting("quiet_hours_start")
    api.get.assert_called_once_with("/api/config/settings/quiet_hours_start")
    assert result["value"] == "22:00"


async def test_set_setting(api):
    api.put.return_value = {"key": "quiet_hours_start", "value": "23:00"}
    result = await set_setting("quiet_hours_start", "23:00")
    api.put.assert_called_once_with(
        "/api/config/settings/quiet_hours_start", {"value": "23:00"}
    )
    assert result["value"] == "23:00"


# --- Monitored Items ---


async def test_list_monitored_items(api):
    api.get.return_value = {
        "items": [{"id": 1, "category": "deals", "name": "camping gear"}]
    }
    result = await list_monitored_items()
    api.get.assert_called_once_with("/api/config/monitored-items")
    assert len(result["items"]) == 1


async def test_list_monitored_items_by_category(api):
    api.get.return_value = {"items": []}
    await list_monitored_items(category="deals")
    api.get.assert_called_once_with("/api/config/monitored-items", category="deals")


async def test_create_monitored_item(api):
    api.post.return_value = {
        "id": 1,
        "category": "deals",
        "name": "camping gear",
        "config": "{}",
    }
    result = await create_monitored_item("deals", "camping gear", "{}")
    api.post.assert_called_once_with(
        "/api/config/monitored-items",
        {
            "category": "deals",
            "name": "camping gear",
            "config": "{}",
        },
    )
    assert result["id"] == 1


async def test_delete_monitored_item(api):
    api.delete.return_value = {"status": "deleted", "id": 1}
    result = await delete_monitored_item(1)
    api.delete.assert_called_once_with("/api/config/monitored-items/1")
    assert result["status"] == "deleted"
