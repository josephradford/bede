import csv
import io
import re


def _parse_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def _parse_csv_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_csv_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_screen_time(date: str, content: str) -> list[dict]:
    rows = _parse_csv(content)
    return [
        {
            "date": date,
            "device": row.get("device", ""),
            "entry_type": row.get("entry_type", ""),
            "name": row.get("name", ""),
            "seconds": _parse_csv_int(row.get("seconds", "0")),
        }
        for row in rows
        if row.get("name")
    ]


def _parse_safari(date: str, content: str) -> list[dict]:
    rows = _parse_csv(content)
    return [
        {
            "date": date,
            "device": row.get("device", ""),
            "domain": row.get("domain", ""),
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "visited_at": row.get("visited_at", ""),
        }
        for row in rows
        if row.get("url")
    ]


def _parse_youtube(date: str, content: str) -> list[dict]:
    rows = _parse_csv(content)
    return [
        {
            "date": date,
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "visited_at": row.get("visited_at", ""),
        }
        for row in rows
        if row.get("url")
    ]


def _parse_music(date: str, content: str) -> list[dict]:
    rows = _parse_csv(content)
    return [
        {
            "date": date,
            "track": row.get("track", ""),
            "artist": row.get("artist", ""),
            "album": row.get("album"),
            "listened_at": row.get("listened_at", ""),
        }
        for row in rows
        if row.get("track") and row.get("artist")
    ]


def _parse_podcasts(date: str, content: str) -> list[dict]:
    rows = _parse_csv(content)
    return [
        {
            "date": date,
            "podcast": row.get("podcast", ""),
            "episode": row.get("episode", ""),
            "duration_seconds": _parse_csv_int(row.get("duration_seconds", "0")),
            "played_at": row.get("played_at", ""),
        }
        for row in rows
        if row.get("episode")
    ]


SESSION_HEADER_RE = re.compile(r"^## (.+)$")
SESSION_META_RE = re.compile(r"^- (\w+): (.+)$")


def _parse_sessions(date: str, content: str, name_field: str) -> list[dict]:
    """Parse markdown session summaries (## Header / - Key: Value / body text). name_field controls whether the header maps to 'project' (claude) or 'task_name' (bede)."""
    sessions = []
    current = None

    for line in content.splitlines():
        header_match = SESSION_HEADER_RE.match(line)
        if header_match:
            if current:
                sessions.append(current)
            current = {"date": date, name_field: header_match.group(1), "summary": ""}
            continue

        if current is None:
            continue

        meta_match = SESSION_META_RE.match(line)
        if meta_match:
            key = meta_match.group(1).lower()
            val = meta_match.group(2).strip()
            if key == "start":
                current["start_time"] = val
            elif key == "end":
                current["end_time"] = val
            elif key == "duration":
                current["duration_min"] = _parse_csv_float(val.split()[0])
            elif key == "turns":
                current["turns"] = _parse_csv_int(val)
        elif line.strip():
            if current.get("summary"):
                current["summary"] += " " + line.strip()
            else:
                current["summary"] = line.strip()

    if current:
        sessions.append(current)
    return sessions


SCREEN_TIME_FILES = {"screentime.csv", "iphone-screentime.csv"}


def parse_vault_payload(payload: dict) -> dict:
    """Parse a vault ingest payload containing {date, files: {filename: content}}. Files are routed by filename prefix to the appropriate CSV or markdown parser."""
    date = payload.get("date", "")
    files = payload.get("files", {})
    result = {
        "screen_time": [],
        "safari_history": [],
        "youtube_history": [],
        "podcasts": [],
        "claude_sessions": [],
        "bede_sessions": [],
        "music_listens": [],
    }

    for filename, content in files.items():
        if filename in SCREEN_TIME_FILES:
            result["screen_time"].extend(_parse_screen_time(date, content))
        elif filename.startswith("safari"):
            result["safari_history"].extend(_parse_safari(date, content))
        elif filename.startswith("youtube"):
            result["youtube_history"].extend(_parse_youtube(date, content))
        elif filename.startswith("podcasts"):
            result["podcasts"].extend(_parse_podcasts(date, content))
        elif filename.startswith("claude-sessions"):
            result["claude_sessions"].extend(_parse_sessions(date, content, "project"))
        elif filename.startswith("bede-sessions"):
            result["bede_sessions"].extend(_parse_sessions(date, content, "task_name"))
        elif filename.startswith("music"):
            result["music_listens"].extend(_parse_music(date, content))

    return result
