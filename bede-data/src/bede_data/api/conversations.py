import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from bede_data.config import settings

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _scan_sessions() -> list[dict]:
    """Walk the sessions directory for subdirectories containing session.jsonl files. Returns lightweight metadata (id, message count, first timestamp) without loading full transcripts."""
    sessions_path = Path(settings.claude_sessions_dir)
    if not sessions_path.exists():
        return []

    sessions = []
    for session_dir in sorted(sessions_path.iterdir()):
        if not session_dir.is_dir():
            continue
        jsonl_file = session_dir / "session.jsonl"
        if not jsonl_file.exists():
            continue

        first_line = None
        line_count = 0
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if first_line is None:
                    try:
                        first_line = json.loads(line)
                    except json.JSONDecodeError:
                        pass
                line_count += 1

        sessions.append(
            {
                "session_id": session_dir.name,
                "message_count": line_count,
                "first_timestamp": first_line.get("timestamp") if first_line else None,
            }
        )

    return sessions


@router.get("")
def list_conversations():
    return {"sessions": _scan_sessions()}


@router.get("/{session_id}")
def get_conversation(session_id: str):
    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    jsonl_file = Path(settings.claude_sessions_dir) / session_id / "session.jsonl"
    if not jsonl_file.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    messages = []
    with open(jsonl_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {"session_id": session_id, "messages": messages}
