"""bede-data-mcp: Thin MCP proxy forwarding tool calls to bede-data's HTTP API."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastmcp import FastMCP

from bede_data_mcp import client  # noqa: F401

mcp = FastMCP("personal-data")


def _datetime_info(dt: datetime) -> dict:
    """Build a rich context dict from a timezone-aware datetime."""
    utc_offset = dt.strftime("%z")
    return {
        "datetime": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M:%S"),
        "day_of_week": dt.strftime("%A"),
        "day_of_month": dt.day,
        "month": dt.month,
        "year": dt.year,
        "week_number": dt.isocalendar()[1],
        "utc_offset": f"{utc_offset[:3]}:{utc_offset[3:]}",
        "timezone": str(dt.tzinfo),
        "unix_timestamp": int(dt.timestamp()),
    }


# ---------------------------------------------------------------------------
# Time tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_current_time(timezone: str = "Australia/Sydney") -> dict:
    """Return the current date and time with rich context.

    Includes day of week, week number, UTC offset, and more. Use this as the
    reliable source of "now" rather than guessing the date.

    Args:
        timezone: Olson timezone name (e.g. 'Australia/Sydney', 'UTC').
    """
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        return {"error": f"Unknown timezone: {timezone}"}
    return _datetime_info(datetime.now(tz))


@mcp.tool()
async def calculate_datetime(
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    base: str = "now",
    timezone: str = "Australia/Sydney",
) -> dict:
    """Add or subtract time from a base datetime and return the result.

    Use negative values to go backwards (e.g. days=-3 for "3 days ago").

    Args:
        days: Days to add (negative to subtract).
        hours: Hours to add (negative to subtract).
        minutes: Minutes to add (negative to subtract).
        seconds: Seconds to add (negative to subtract).
        base: Starting datetime -- 'now' or an ISO 8601 string (e.g. '2026-05-03T10:00:00').
        timezone: Olson timezone name. Used to resolve 'now' and for the output.
    """
    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        return {"error": f"Unknown timezone: {timezone}"}

    if base == "now":
        base_dt = datetime.now(tz)
    else:
        try:
            parsed = datetime.fromisoformat(base)
            base_dt = (
                parsed.astimezone(tz) if parsed.tzinfo else parsed.replace(tzinfo=tz)
            )
        except ValueError:
            return {"error": f"Invalid base datetime: {base}"}

    result = base_dt + timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    )
    return _datetime_info(result)


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
# Usage data tools
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
    return await client.get("/api/usage/screen-time", **kwargs)


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
    return await client.get("/api/usage/safari", **kwargs)


@mcp.tool()
async def get_youtube_history(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return YouTube page visits for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/usage/youtube", date=date, timezone=timezone)


@mcp.tool()
async def get_podcasts(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return podcast episodes played on a given local date.

    Each entry includes playhead_seconds (how far the user listened) and play_count
    (times fully completed). An episode with play_count=0 and low playhead_seconds
    was only briefly sampled, not meaningfully listened to.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/usage/podcasts", date=date, timezone=timezone)


@mcp.tool()
async def get_claude_sessions(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return Claude Code session summaries for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/usage/claude-sessions", date=date, timezone=timezone)


@mcp.tool()
async def get_bede_sessions(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return Bede (Telegram AI assistant) session summaries for a given local date.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/usage/bede-sessions", date=date, timezone=timezone)


# ---------------------------------------------------------------------------
# Location tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_location_summary(date: str, timezone: str = "Australia/Sydney") -> dict:
    """Return where Joe was during a given day as a list of named stops with local arrival/departure times.

    This is the primary location tool. It clusters GPS points, reverse geocodes coordinates into
    place names, and converts all timestamps to the requested timezone.

    Args:
        date: Local date -- 'YYYY-MM-DD', 'today', or 'yesterday'.
        timezone: Olson timezone name.
    """
    return await client.get("/api/location/summary", date=date, tz=timezone)


@mcp.tool()
async def get_location_raw(from_date: str, to_date: str) -> dict:
    """Return raw OwnTracks GPS points for debugging or custom analysis.

    Prefer get_location_summary for normal use — it returns named stops with local times.
    This tool returns unsummarised points with UTC epoch timestamps and bare lat/lon coordinates.

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


@mcp.tool()
async def update_monitored_item(
    item_id: int,
    name: str | None = None,
    config: str | None = None,
    enabled: bool | None = None,
) -> dict:
    """Update a monitored item's name, config, or enabled status.

    Args:
        item_id: ID of the item to update.
        name: New human-readable name.
        config: New JSON config string.
        enabled: Set enabled/disabled.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if config is not None:
        body["config"] = config
    if enabled is not None:
        body["enabled"] = enabled
    return await client.put(f"/api/config/monitored-items/{item_id}", body)


# ---------------------------------------------------------------------------
# Deal monitoring tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def record_price_check(
    monitored_item_id: int,
    url: str,
    price: float | None = None,
    currency: str | None = None,
    in_stock: bool | None = None,
    notes: str | None = None,
) -> dict:
    """Record a price check observation after scraping a retailer page.

    Call this after visiting a product URL to persist the price and stock status.
    The system tracks history so price drops and restocks can be detected.

    Args:
        monitored_item_id: ID of the monitored item this check belongs to.
        url: The product page URL that was checked.
        price: The observed price (omit if product page doesn't show a price).
        currency: Currency code (e.g. 'AUD', 'USD'). Omit to use the API default (AUD).
        in_stock: Whether the product is currently in stock.
        notes: Optional notes (e.g. 'sale ends Friday', 'clearance').
    """
    body: dict = {"monitored_item_id": monitored_item_id, "url": url}
    if price is not None:
        body["price"] = price
    if currency is not None:
        body["currency"] = currency
    if in_stock is not None:
        body["in_stock"] = in_stock
    if notes is not None:
        body["notes"] = notes
    return await client.post("/api/deals/price-checks", body)


@mcp.tool()
async def get_price_history(
    monitored_item_id: int,
    limit: int | None = None,
    url: str | None = None,
) -> dict:
    """Get price check history for a monitored item.

    Returns checks in reverse chronological order. Compare the most recent
    check against previous ones to detect price drops or restocks.

    Args:
        monitored_item_id: ID of the monitored item.
        limit: Max number of checks to return (default 50).
        url: Filter to a specific product URL.
    """
    kwargs: dict = {}
    if limit is not None:
        kwargs["limit"] = limit
    if url is not None:
        kwargs["url"] = url
    return await client.get(f"/api/deals/price-history/{monitored_item_id}", **kwargs)


@mcp.tool()
async def report_dead_url(
    url: str, category: str | None = None, error: str | None = None
) -> dict:
    """Report a URL that failed to load or returned an error.

    Call this when a product page returns 404, 403, redirects to a homepage,
    or otherwise fails. The system tracks failure counts — URLs with repeated
    failures can be skipped in future checks.

    Args:
        url: The URL that failed.
        category: Category for grouping (e.g. 'deal', 'news').
        error: Description of the failure (e.g. '404 Not Found', 'redirect to homepage').
    """
    body: dict = {"url": url}
    if category is not None:
        body["category"] = category
    if error is not None:
        body["last_error"] = error
    return await client.post("/api/deals/dead-urls", body)


@mcp.tool()
async def list_dead_urls(category: str | None = None) -> dict:
    """List known dead URLs to skip during scraping.

    Check this before attempting to scrape — URLs in this list have
    previously failed and may waste time.

    Args:
        category: Filter by category (e.g. 'deal', 'news').
    """
    kwargs: dict = {}
    if category is not None:
        kwargs["category"] = category
    return await client.get("/api/deals/dead-urls", **kwargs)


@mcp.tool()
async def update_dead_url(
    url_id: int,
    disabled: bool | None = None,
    last_error: str | None = None,
) -> dict:
    """Update a dead URL entry (e.g. to disable it permanently).

    Args:
        url_id: ID of the dead URL entry.
        disabled: Set to true to permanently skip this URL.
        last_error: Update the error description.
    """
    body: dict = {}
    if disabled is not None:
        body["disabled"] = disabled
    if last_error is not None:
        body["last_error"] = last_error
    return await client.put(f"/api/deals/dead-urls/{url_id}", body)


# ---------------------------------------------------------------------------
# News curation tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def save_article(
    url: str,
    title: str,
    source_name: str,
    category: str | None = None,
    summary: str | None = None,
) -> dict:
    """Save an article found during news curation.

    Handles deduplication by URL — if the article already exists, returns
    the existing record with already_existed=true instead of creating a
    duplicate.

    Args:
        url: The article URL (used as dedup key).
        title: Article headline.
        source_name: Where it was found (e.g. 'Hacker News', 'TLDR AI').
        category: Topic category (e.g. 'ai', 'public_sector', 'platform_tech').
        summary: Brief summary of the article content.
    """
    body: dict = {"url": url, "title": title, "source_name": source_name}
    if category is not None:
        body["category"] = category
    if summary is not None:
        body["summary"] = summary
    return await client.post("/api/news/articles", body)


@mcp.tool()
async def list_articles(
    category: str | None = None,
    source_name: str | None = None,
    unsent: bool | None = None,
    limit: int | None = None,
) -> dict:
    """List saved articles, optionally filtered.

    Use unsent=true to get articles not yet included in any digest — this
    is the primary query for building a news digest.

    Args:
        category: Filter by topic category.
        source_name: Filter by source name.
        unsent: If true, only return articles not yet in a digest.
        limit: Max articles to return (default 50).
    """
    kwargs: dict = {}
    if category is not None:
        kwargs["category"] = category
    if source_name is not None:
        kwargs["source_name"] = source_name
    if unsent is not None:
        kwargs["unsent"] = unsent
    if limit is not None:
        kwargs["limit"] = limit
    return await client.get("/api/news/articles", **kwargs)


@mcp.tool()
async def check_article_exists(url: str) -> dict:
    """Check if an article URL has already been saved (deduplication check).

    Args:
        url: The article URL to check.
    """
    return await client.get("/api/news/articles/exists", url=url)


@mcp.tool()
async def mark_article_in_digest(article_id: int, digest_date: str) -> dict:
    """Mark an article as included in a digest.

    Call this after including an article in a news digest delivery so it
    won't appear in future unsent queries.

    Args:
        article_id: ID of the article.
        digest_date: The date of the digest (YYYY-MM-DD format).
    """
    return await client.put(
        f"/api/news/articles/{article_id}/digest",
        {"digest_date": digest_date},
    )


# ---------------------------------------------------------------------------
# Data pipeline tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_data_freshness() -> dict:
    """Return data freshness status for all sources (when each source last received data)."""
    return await client.get("/api/freshness")


@mcp.tool()
async def get_storage() -> dict:
    """Return database storage usage: total size and row counts per table."""
    return await client.get("/api/storage")


# ---------------------------------------------------------------------------
# Conversation history tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_conversations() -> dict:
    """List all past conversation sessions with metadata (message count, first timestamp)."""
    return await client.get("/api/conversations")


@mcp.tool()
async def get_conversation(session_id: str) -> dict:
    """Get the full transcript of a past conversation session.

    Args:
        session_id: The session ID to retrieve.
    """
    return await client.get(f"/api/conversations/{session_id}")


# ---------------------------------------------------------------------------
# Task history tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_task_history(
    task_name: str | None = None, limit: int | None = None
) -> dict:
    """Get scheduled task execution history.

    Args:
        task_name: Filter by task name (omit for all tasks).
        limit: Maximum number of records to return.
    """
    kwargs: dict = {}
    if task_name is not None:
        kwargs["task_name"] = task_name
    if limit is not None:
        kwargs["limit"] = limit
    return await client.get("/api/tasks/history", **kwargs)


# ---------------------------------------------------------------------------
# Vault publish queue
# ---------------------------------------------------------------------------


@mcp.tool()
async def enqueue_vault_item(
    content_type: str, content: str, vault_path: str | None = None
) -> dict:
    """Queue content for publishing to the Obsidian vault.

    Use this for journal entries, captured ideas, or any content the user wants in their vault.
    A background process picks items off the queue and writes them as Markdown files.

    Args:
        content_type: Type of content (e.g. 'journal', 'idea', 'note').
        content: The Markdown content to publish.
        vault_path: Target path within the vault (e.g. 'Journal/2026-04-30.md'). Optional.
    """
    body: dict = {"content_type": content_type, "content": content}
    if vault_path is not None:
        body["vault_path"] = vault_path
    return await client.post("/api/vault-queue", body)
