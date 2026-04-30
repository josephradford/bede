from bede_data_mcp.server import create_goal, get_goal, list_goals, update_goal


async def test_create_goal(api):
    api.post.return_value = {"id": 1, "name": "Read 2 books in May", "status": "active"}
    result = await create_goal("Read 2 books in May")
    api.post.assert_called_once_with("/api/goals", {"name": "Read 2 books in May"})
    assert result["id"] == 1


async def test_create_goal_with_details(api):
    api.post.return_value = {"id": 2, "name": "AWS cert", "deadline": "2026-09-01"}
    await create_goal(
        "AWS cert",
        description="Pass AWS Solutions Architect Associate",
        deadline="2026-09-01",
        measurable_indicators="Pass the exam",
    )
    api.post.assert_called_once_with(
        "/api/goals",
        {
            "name": "AWS cert",
            "description": "Pass AWS Solutions Architect Associate",
            "deadline": "2026-09-01",
            "measurable_indicators": "Pass the exam",
        },
    )


async def test_list_goals(api):
    api.get.return_value = {
        "goals": [{"id": 1, "name": "Read 2 books", "status": "active"}]
    }
    result = await list_goals()
    api.get.assert_called_once_with("/api/goals")
    assert len(result["goals"]) == 1


async def test_list_goals_by_status(api):
    api.get.return_value = {"goals": []}
    await list_goals(status="completed")
    api.get.assert_called_once_with("/api/goals", status="completed")


async def test_get_goal(api):
    api.get.return_value = {"id": 1, "name": "Read 2 books", "status": "active"}
    result = await get_goal(1)
    api.get.assert_called_once_with("/api/goals/1")
    assert result["name"] == "Read 2 books"


async def test_update_goal(api):
    api.put.return_value = {"id": 1, "name": "Read 3 books", "status": "active"}
    result = await update_goal(1, name="Read 3 books")
    api.put.assert_called_once_with("/api/goals/1", {"name": "Read 3 books"})
    assert result["name"] == "Read 3 books"


async def test_update_goal_status(api):
    api.put.return_value = {"id": 1, "name": "Read 2 books", "status": "completed"}
    await update_goal(1, status="completed")
    api.put.assert_called_once_with("/api/goals/1", {"status": "completed"})


async def test_update_goal_deadline(api):
    api.put.return_value = {"id": 1, "deadline": "2026-12-31"}
    await update_goal(1, deadline="2026-12-31")
    api.put.assert_called_once_with("/api/goals/1", {"deadline": "2026-12-31"})
