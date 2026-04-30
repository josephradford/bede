"""bede-data-mcp: Thin MCP proxy forwarding tool calls to bede-data's HTTP API."""

import os

from fastmcp import FastMCP

from bede_data_mcp import client  # noqa: F401

mcp = FastMCP("personal-data")


# ---------------------------------------------------------------------------
# Health tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_sleep(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return sleep summary for the night ending on the given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/sleep", date=date, timezone=timezone)


@mcp.tool()
async def get_activity(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return daily activity summary (steps, active energy, exercise minutes, stand hours).

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/activity", date=date, timezone=timezone)


@mcp.tool()
async def get_workouts(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return workouts recorded on a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/workouts", date=date, timezone=timezone)


@mcp.tool()
async def get_heart_rate(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return resting heart rate and HRV for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/heart-rate", date=date, timezone=timezone)


@mcp.tool()
async def get_wellbeing(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return mindfulness minutes and state of mind data for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/wellbeing", date=date, timezone=timezone)


@mcp.tool()
async def get_medications(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return medications logged on a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/health/medications", date=date, timezone=timezone)


# ---------------------------------------------------------------------------
# Vault data tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_screen_time(
    date: str,
    device: str | None = None,
    top_n: int | None = None,
    timezone: str = "Australia/Sydney",
) -> dict:
    """Return app and web domain screen time usage for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        device: 'mac', 'iphone', or omit for all devices.
        top_n: Return only the top N entries by duration.
        timezone: Olson timezone name.
    """
    kwargs = {"date": date, "timezone": timezone}
    if device is not None:
        kwargs["device"] = device
    if top_n is not None:
        kwargs["top_n"] = top_n
    return await client.get("/api/vault/screen-time", **kwargs)


@mcp.tool()
async def get_safari_history(
    date: str,
    device: str | None = None,
    domain_filter: str | None = None,
    top_n: int | None = None,
    timezone: str = "Australia/Sydney",
) -> dict:
    """Return Safari page visits for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        device: 'mac', 'iphone', or omit for all devices.
        domain_filter: Filter by domain substring (e.g. 'github.com').
        top_n: Limit number of results.
        timezone: Olson timezone name.
    """
    kwargs = {"date": date, "timezone": timezone}
    if device is not None:
        kwargs["device"] = device
    if domain_filter is not None:
        kwargs["domain"] = domain_filter
    if top_n is not None:
        kwargs["top_n"] = top_n
    return await client.get("/api/vault/safari", **kwargs)


@mcp.tool()
async def get_youtube_history(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return YouTube page visits for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/vault/youtube", date=date, timezone=timezone)


@mcp.tool()
async def get_podcasts(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return podcast episodes played on a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/vault/podcasts", date=date, timezone=timezone)


@mcp.tool()
async def get_claude_sessions(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return Claude Code session summaries for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/vault/claude-sessions", date=date, timezone=timezone)


@mcp.tool()
async def get_bede_sessions(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return Bede (Telegram AI assistant) session summaries for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/vault/bede-sessions", date=date, timezone=timezone)


# ---------------------------------------------------------------------------
# Location tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_location_summary(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return summarised stops for a given local date with place names and arrival/departure times.

    Clusters GPS points into named locations via reverse geocoding.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/location/summary", date=date, tz=timezone)


@mcp.tool()
async def get_location_raw(from_date: str, to_date: str) -> dict:
    """Return raw GPS points for a local date range without summarisation.

    Args:
        from_date: Start local date ('YYYY-MM-DD').
        to_date: End local date ('YYYY-MM-DD').
    """
    return await client.get("/api/location/raw", from_date=from_date, to_date=to_date)


# ---------------------------------------------------------------------------
# Weather tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_weather() -> dict:
    """Return current weather observations and 7-day forecast for the configured location.

    Includes temperature, conditions, wind, humidity, rain chance, UV index, and sunrise/sunset.
    Data sourced from the Australian Bureau of Meteorology.
    """
    return await client.get("/api/weather")


@mcp.tool()
async def get_air_quality(site_id: str | None = None) -> dict:
    """Return current air quality index and alerts.

    Args:
        site_id: Optional monitoring site ID. Omit for default location.
    """
    kwargs = {}
    if site_id is not None:
        kwargs["site_id"] = site_id
    return await client.get("/api/air-quality", **kwargs)


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_memory(
    content: str,
    type: str,
    source_conversation: str | None = None,
    supersedes: int | None = None,
) -> dict:
    """Store a new memory. Memories are facts, preferences, or corrections that persist across conversations.

    Args:
        content: The memory content to store.
        type: Memory type -- 'fact', 'preference', 'correction', or 'commitment'.
        source_conversation: Optional session ID of the conversation that produced this memory.
        supersedes: Optional ID of a previous memory this one corrects (marks the old one inactive).
    """
    body: dict = {"content": content, "type": type}
    if source_conversation is not None:
        body["source_conversation"] = source_conversation
    if supersedes is not None:
        body["supersedes"] = supersedes
    return await client.post("/api/memories", body)


@mcp.tool()
async def list_memories(
    type: str | None = None,
    search: str | None = None,
    limit: int | None = None,
) -> dict:
    """List active memories, optionally filtered by type or search term.

    Args:
        type: Filter by type -- 'fact', 'preference', 'correction', or 'commitment'.
        search: Search term to filter memory content.
        limit: Maximum number of memories to return.
    """
    kwargs: dict = {}
    if type is not None:
        kwargs["type"] = type
    if search is not None:
        kwargs["search"] = search
    if limit is not None:
        kwargs["limit"] = limit
    return await client.get("/api/memories", **kwargs)


@mcp.tool()
async def update_memory(
    memory_id: int,
    content: str | None = None,
    type: str | None = None,
) -> dict:
    """Update an existing memory's content or type.

    Args:
        memory_id: ID of the memory to update.
        content: New content (omit to keep current).
        type: New type (omit to keep current).
    """
    body: dict = {}
    if content is not None:
        body["content"] = content
    if type is not None:
        body["type"] = type
    return await client.put(f"/api/memories/{memory_id}", body)


@mcp.tool()
async def delete_memory(memory_id: int) -> dict:
    """Soft-delete a memory (marks it inactive, does not remove the row).

    Args:
        memory_id: ID of the memory to delete.
    """
    return await client.delete(f"/api/memories/{memory_id}")


@mcp.tool()
async def reference_memory(memory_id: int) -> dict:
    """Touch a memory's last-referenced timestamp for relevance ranking.

    Call this when a memory is actively used in a conversation to track which memories are still relevant.

    Args:
        memory_id: ID of the memory being referenced.
    """
    return await client.post(f"/api/memories/{memory_id}/reference")


# ---------------------------------------------------------------------------
# Goal tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_goal(
    name: str,
    description: str | None = None,
    deadline: str | None = None,
    measurable_indicators: str | None = None,
) -> dict:
    """Create a new goal. Goals are commitments the user wants to track and be held accountable for.

    Args:
        name: Short name for the goal.
        description: Detailed description of what achieving this goal means.
        deadline: Target date ('YYYY-MM-DD') or omit for open-ended goals.
        measurable_indicators: How progress or completion will be measured.
    """
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description
    if deadline is not None:
        body["deadline"] = deadline
    if measurable_indicators is not None:
        body["measurable_indicators"] = measurable_indicators
    return await client.post("/api/goals", body)


@mcp.tool()
async def list_goals(status: str | None = None) -> dict:
    """List goals, optionally filtered by status.

    Args:
        status: Filter by status -- 'active', 'completed', or 'dropped'.
    """
    kwargs: dict = {}
    if status is not None:
        kwargs["status"] = status
    return await client.get("/api/goals", **kwargs)


@mcp.tool()
async def get_goal(goal_id: int) -> dict:
    """Get a single goal by ID.

    Args:
        goal_id: ID of the goal to retrieve.
    """
    return await client.get(f"/api/goals/{goal_id}")


@mcp.tool()
async def update_goal(
    goal_id: int,
    name: str | None = None,
    description: str | None = None,
    deadline: str | None = None,
    measurable_indicators: str | None = None,
    status: str | None = None,
) -> dict:
    """Update an existing goal's details or status.

    Args:
        goal_id: ID of the goal to update.
        name: New name (omit to keep current).
        description: New description (omit to keep current).
        deadline: New deadline date (omit to keep current).
        measurable_indicators: Updated measurement criteria (omit to keep current).
        status: New status -- 'active', 'completed', or 'dropped' (omit to keep current).
    """
    body: dict = {}
    for field in ("name", "description", "deadline", "measurable_indicators", "status"):
        val = locals()[field]
        if val is not None:
            body[field] = val
    return await client.put(f"/api/goals/{goal_id}", body)

# ---------------------------------------------------------------------------
# Analytics tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_analytics_flags(
    severity: str | None = None,
    acknowledged: bool | None = None,
    limit: int | None = None,
) -> dict:
    """Get computed analytics flags (wellbeing signals, goal staleness, etc.).

    Flags are produced by the Analytics Engine from raw data. Use these to understand
    patterns and trends that inform coaching conversations.

    Args:
        severity: Filter by severity -- 'info', 'nudge', 'concern', or 'alert'.
        acknowledged: Filter by acknowledgement status (true/false).
        limit: Maximum number of flags to return.
    """
    kwargs: dict = {}
    if severity is not None:
        kwargs["severity"] = severity
    if acknowledged is not None:
        kwargs["acknowledged"] = acknowledged
    if limit is not None:
        kwargs["limit"] = limit
    return await client.get("/api/analytics/flags", **kwargs)


@mcp.tool()
async def acknowledge_flag(flag_id: int) -> dict:
    """Mark an analytics flag as acknowledged so it is not raised again.

    Args:
        flag_id: ID of the flag to acknowledge.
    """
    return await client.put(f"/api/analytics/flags/{flag_id}/acknowledge")


# ---------------------------------------------------------------------------
# Config tools — schedules
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_schedules() -> dict:
    """List all scheduled task definitions."""
    return await client.get("/api/config/schedules")


@mcp.tool()
async def create_schedule(
    task_name: str,
    cron_expression: str,
    prompt: str,
    model: str | None = None,
    timeout_seconds: int | None = None,
    interactive: bool | None = None,
    enabled: bool | None = None,
) -> dict:
    """Create a new scheduled task.

    Args:
        task_name: Unique name for the task.
        cron_expression: Cron schedule (e.g. '0 8 * * 1-5' for weekday mornings at 8am).
        prompt: The prompt text sent to Claude when the task fires.
        model: Claude model to use (omit for default).
        timeout_seconds: Maximum execution time in seconds (omit for default 300).
        interactive: Whether the task can yield to the user for input (omit for default false).
        enabled: Whether the task is active (omit for default true).
    """
    body: dict = {
        "task_name": task_name,
        "cron_expression": cron_expression,
        "prompt": prompt,
    }
    for field in ("model", "timeout_seconds", "interactive", "enabled"):
        val = locals()[field]
        if val is not None:
            body[field] = val
    return await client.post("/api/config/schedules", body)


@mcp.tool()
async def update_schedule(
    schedule_id: int,
    cron_expression: str | None = None,
    prompt: str | None = None,
    model: str | None = None,
    timeout_seconds: int | None = None,
    interactive: bool | None = None,
    enabled: bool | None = None,
) -> dict:
    """Update an existing scheduled task.

    Args:
        schedule_id: ID of the schedule to update.
        cron_expression: New cron schedule (omit to keep current).
        prompt: New prompt text (omit to keep current).
        model: New model (omit to keep current).
        timeout_seconds: New timeout (omit to keep current).
        interactive: New interactive setting (omit to keep current).
        enabled: New enabled setting (omit to keep current).
    """
    body: dict = {}
    for field in (
        "cron_expression",
        "prompt",
        "model",
        "timeout_seconds",
        "interactive",
        "enabled",
    ):
        val = locals()[field]
        if val is not None:
            body[field] = val
    return await client.put(f"/api/config/schedules/{schedule_id}", body)


# ---------------------------------------------------------------------------
# Config tools — settings
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_settings() -> dict:
    """List all key-value settings (quiet hours, coaching thresholds, etc.)."""
    return await client.get("/api/config/settings")


@mcp.tool()
async def get_setting(key: str) -> dict:
    """Get a single setting by key.

    Args:
        key: The setting key (e.g. 'quiet_hours_start', 'sleep_target_hours').
    """
    return await client.get(f"/api/config/settings/{key}")


@mcp.tool()
async def set_setting(key: str, value: str) -> dict:
    """Set a key-value setting. Creates or updates.

    Args:
        key: The setting key.
        value: The setting value (stored as a string).
    """
    return await client.put(f"/api/config/settings/{key}", {"value": value})


# ---------------------------------------------------------------------------
# Config tools — monitored items
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_monitored_items(category: str | None = None) -> dict:
    """List monitored items (deal categories, content sources, etc.).

    Args:
        category: Filter by category (e.g. 'deals', 'news').
    """
    kwargs: dict = {}
    if category is not None:
        kwargs["category"] = category
    return await client.get("/api/config/monitored-items", **kwargs)


@mcp.tool()
async def create_monitored_item(category: str, name: str, config: str) -> dict:
    """Add a new monitored item (e.g. a deal category to track or a news source).

    Args:
        category: Item category (e.g. 'deals', 'news').
        name: Human-readable name.
        config: JSON string with category-specific configuration.
    """
    return await client.post(
        "/api/config/monitored-items",
        {"category": category, "name": name, "config": config},
    )


@mcp.tool()
async def delete_monitored_item(item_id: int) -> dict:
    """Remove a monitored item (soft-delete).

    Args:
        item_id: ID of the item to remove.
    """
    return await client.delete(f"/api/config/monitored-items/{item_id}")


if __name__ == "__main__":
    port = int(os.environ.get("DATA_MCP_PORT", "8002"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
