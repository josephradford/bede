from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    allowed_user_id: int = 0
    claude_model: str = "claude-sonnet-4-5-20250514"
    claude_workdir: str = "/app"
    claude_timeout_seconds: int = 300
    session_timeout_minutes: int = 120
    interactive_idle_timeout_minutes: int = 30
    interactive_max_age_hours: int = 2
    timezone: str = "Australia/Sydney"
    bede_data_url: str = "http://bede-data:8001"
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    vault_path: str = "/vault"

    model_config = {"env_prefix": "", "case_sensitive": False}
