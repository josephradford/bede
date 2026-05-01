import logging
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

REFLECTION_REL_PATH = os.path.join("Bede", "reflection-memory.md")

_HEADER = (
    "# Reflection Memory\n\n"
    "Corrections and preferences Joe has provided about Evening Reflections.\n"
    "Bede reads this at the start of each reflection to avoid repeating mistakes.\n\n"
    "## Corrections\n\n"
)


def _git_commit_push(vault_path: str, file_path: str):
    try:
        subprocess.run(
            ["git", "-C", vault_path, "add", file_path],
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "-C", vault_path, "commit", "-m", "reflection: save correction"],
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "-C", vault_path, "push"],
            capture_output=True,
            timeout=30,
        )
    except Exception as e:
        log.warning("Failed to commit reflection correction: %s", e)


def append_correction(text: str, vault_path: str, timezone: str):
    full_path = os.path.join(vault_path, REFLECTION_REL_PATH)
    now = datetime.now(ZoneInfo(timezone))
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    if not os.path.isfile(full_path):
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(_HEADER)

    with open(full_path, "a") as f:
        f.write(f"- [{timestamp}] {text}\n")

    _git_commit_push(vault_path, full_path)
