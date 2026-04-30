from bede_data_mcp.server import (
    get_activity,
    get_heart_rate,
    get_medications,
    get_sleep,
    get_wellbeing,
    get_workouts,
)


async def test_get_sleep(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "total_hours": 7.5,
        "bedtime": "22:30",
        "wake_time": "06:00",
        "phases": [],
    }
    result = await get_sleep("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/sleep", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["total_hours"] == 7.5


async def test_get_sleep_custom_timezone(api):
    api.get.return_value = {"date": "2026-04-30", "total_hours": 8.0}
    await get_sleep("2026-04-30", timezone="America/New_York")
    api.get.assert_called_once_with(
        "/api/health/sleep", date="2026-04-30", timezone="America/New_York"
    )


async def test_get_activity(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "steps": 8423,
        "active_energy": 512,
        "exercise_minutes": 38,
        "stand_hours": 10,
    }
    result = await get_activity("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/activity", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["steps"] == 8423


async def test_get_workouts(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "workouts": [{"workout_type": "running", "duration_minutes": 30}],
    }
    result = await get_workouts("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/workouts", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert len(result["workouts"]) == 1


async def test_get_heart_rate(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "resting_heart_rate": 58,
        "heart_rate_variability": 42,
    }
    result = await get_heart_rate("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/heart-rate", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["resting_heart_rate"] == 58


async def test_get_wellbeing(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "mindful_minutes": 10,
        "state_of_mind": [],
    }
    result = await get_wellbeing("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/wellbeing", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert result["mindful_minutes"] == 10


async def test_get_medications(api):
    api.get.return_value = {
        "date": "2026-04-30",
        "medications": [{"medication": "vitamin D", "quantity": 1}],
    }
    result = await get_medications("2026-04-30")
    api.get.assert_called_once_with(
        "/api/health/medications", date="2026-04-30", timezone="Australia/Sydney"
    )
    assert len(result["medications"]) == 1
