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


if __name__ == "__main__":
    port = int(os.environ.get("DATA_MCP_PORT", "8002"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
