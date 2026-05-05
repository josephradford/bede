import logging
from pathlib import Path

from bede_data.config import settings


def configure_payload_logging() -> None:
    """Configure health payload logger to append raw payloads to a JSONL file."""
    log_path = Path(settings.sqlite_db_path).parent / "hae_payloads.jsonl"
    handler = logging.FileHandler(log_path, mode="a")
    handler.setFormatter(logging.Formatter("%(asctime)s\t%(message)s"))
    logger = logging.getLogger("bede_data.ingest.health_payloads")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
