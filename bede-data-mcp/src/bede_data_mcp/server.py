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


if __name__ == "__main__":
    port = int(os.environ.get("DATA_MCP_PORT", "8002"))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
