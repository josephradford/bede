import os

import pytest

from bede_core.config import Settings, check_model_config


def test_settings_defaults():
    """Settings load with sensible defaults when no env vars are set."""
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("ALLOWED_USER_ID", None)
    os.environ.pop("MODEL", None)

    s = Settings(telegram_bot_token="test-token", allowed_user_id=12345)
    assert s.telegram_bot_token == "test-token"
    assert s.allowed_user_id == 12345
    assert s.model == ""
    assert s.persona_path == "/app/CLAUDE.md"
    assert s.max_agent_steps == 15
    assert s.agent_timeout_seconds == 300
    assert s.session_timeout_minutes == 120
    assert s.timezone == "Australia/Sydney"
    assert s.bede_data_url == "http://bede-data:8001"
    assert s.interactive_idle_timeout_minutes == 30
    assert s.interactive_max_age_hours == 2
    assert s.quiet_hours_start == 22
    assert s.quiet_hours_end == 7
    assert s.vault_path == "/vault"


def test_settings_from_env(monkeypatch):
    """Settings can be overridden via environment variables."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-token")
    monkeypatch.setenv("ALLOWED_USER_ID", "99999")
    monkeypatch.setenv("MODEL", "openrouter:vendor/some-model")
    monkeypatch.setenv("MAX_AGENT_STEPS", "7")
    monkeypatch.setenv("SESSION_TIMEOUT_MINUTES", "60")
    monkeypatch.setenv("TIMEZONE", "US/Eastern")
    monkeypatch.setenv("BEDE_DATA_URL", "http://localhost:8001")

    s = Settings()
    assert s.telegram_bot_token == "my-token"
    assert s.allowed_user_id == 99999
    assert s.model == "openrouter:vendor/some-model"
    assert s.max_agent_steps == 7
    assert s.session_timeout_minutes == 60
    assert s.timezone == "US/Eastern"
    assert s.bede_data_url == "http://localhost:8001"


class TestCheckModelConfig:
    def test_empty_model_fails(self):
        with pytest.raises(ValueError, match="MODEL is not set"):
            check_model_config("", {})

    def test_model_without_provider_prefix_fails(self):
        with pytest.raises(ValueError, match="provider:name"):
            check_model_config("some-model", {})

    def test_openrouter_requires_its_key(self):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            check_model_config("openrouter:vendor/m", {})

    def test_openrouter_with_key_passes(self):
        check_model_config("openrouter:vendor/m", {"OPENROUTER_API_KEY": "k"})

    def test_unknown_provider_is_not_checked(self):
        check_model_config("somevendor:m", {})


def test_data_collection_denied_by_default():
    assert Settings().openrouter_deny_data_collection is True
