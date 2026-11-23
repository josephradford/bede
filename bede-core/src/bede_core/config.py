from collections.abc import Mapping

from pydantic_settings import BaseSettings

# Env var holding the API key for each supported provider prefix. Pydantic AI
# reads these from the environment itself; this table only powers the startup check.
PROVIDER_KEY_ENV = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    allowed_user_id: int = 0
    model: str = ""
    persona_path: str = "/app/CLAUDE.md"
    agent_timeout_seconds: int = 300
    max_agent_steps: int = 15
    openrouter_deny_data_collection: bool = True
    session_timeout_minutes: int = 120
    interactive_idle_timeout_minutes: int = 30
    interactive_max_age_hours: int = 2
    timezone: str = "Australia/Sydney"
    bede_data_url: str = "http://bede-data:8001"
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    vault_path: str = "/vault"
    mcp_config_path: str = "/app/mcp.json"

    model_config = {"env_prefix": "", "case_sensitive": False}


def check_model_config(model: str, environ: Mapping[str, str]) -> None:
    """Fail fast at startup if the model or its provider key is missing."""
    if not model:
        raise ValueError(
            "MODEL is not set (expected provider:name, "
            "e.g. openrouter:<vendor>/<model>)"
        )
    if ":" not in model:
        raise ValueError(f"MODEL must be provider:name, got '{model}'")
    key_env = PROVIDER_KEY_ENV.get(model.split(":", 1)[0])
    if key_env and not environ.get(key_env):
        raise ValueError(f"{key_env} is not set (needed for MODEL={model})")
