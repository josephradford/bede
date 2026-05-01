import os


def test_settings_defaults():
    """Settings load with sensible defaults when no env vars are set."""
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("ALLOWED_USER_ID", None)
    from bede_core.config import Settings

    s = Settings(telegram_bot_token="test-token", allowed_user_id=12345)
    assert s.telegram_bot_token == "test-token"
    assert s.allowed_user_id == 12345
    assert s.claude_model == "claude-sonnet-4-5-20250514"
    assert s.claude_workdir == "/app"
    assert s.session_timeout_minutes == 120
    assert s.timezone == "Australia/Sydney"
    assert s.bede_data_url == "http://bede-data:8001"
    assert s.claude_timeout_seconds == 300
    assert s.interactive_idle_timeout_minutes == 30
    assert s.interactive_max_age_hours == 2
    assert s.quiet_hours_start == 22
    assert s.quiet_hours_end == 7
    assert s.vault_path == "/vault"


def test_settings_from_env(monkeypatch):
    """Settings can be overridden via environment variables."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "99999")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("SESSION_TIMEOUT_MINUTES", "60")
    monkeypatch.setenv("TIMEZONE", "US/Eastern")
    monkeypatch.setenv("BEDE_DATA_URL", "http://localhost:8001")
    from bede_core.config import Settings

    s = Settings()
    assert s.telegram_bot_token == "my-token"
    assert s.allowed_user_id == 99999
    assert s.claude_model == "claude-haiku-4-5-20251001"
    assert s.session_timeout_minutes == 60
    assert s.timezone == "US/Eastern"
    assert s.bede_data_url == "http://localhost:8001"
