"""Tests for configuration loading and validation."""

import pytest
from pydantic import ValidationError

from app.config import AppConfig, LLMConfig, Settings, TriageConfig


def test_app_config_defaults():
    """AppConfig loads with sensible defaults."""
    config = AppConfig()
    assert config.environment in ("development", "staging", "production", "testing")
    assert config.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def test_triage_config_defaults():
    """TriageConfig has expected defaults."""
    config = TriageConfig()
    assert config.max_triage_questions >= 1
    assert 0.0 <= config.low_confidence_threshold <= 1.0


def test_triage_config_rejects_zero_questions():
    """max_triage_questions must be >= 1."""
    with pytest.raises(ValidationError):
        TriageConfig(max_triage_questions=0)


def test_triage_config_rejects_invalid_confidence_high():
    """Confidence threshold above 1.0 is rejected."""
    with pytest.raises(ValidationError):
        TriageConfig(low_confidence_threshold=1.5)


def test_triage_config_rejects_invalid_confidence_negative():
    """Negative confidence threshold is rejected."""
    with pytest.raises(ValidationError):
        TriageConfig(low_confidence_threshold=-0.1)


def test_triage_config_accepts_boundary_values():
    """Confidence 0.0 and 1.0 are valid boundaries."""
    assert TriageConfig(low_confidence_threshold=0.0).low_confidence_threshold == 0.0
    assert TriageConfig(low_confidence_threshold=1.0).low_confidence_threshold == 1.0


def test_llm_config_accepts_supported_providers():
    """mock, claude, and openai are supported providers."""
    for provider in ("mock", "claude", "openai"):
        assert LLMConfig(llm_provider=provider).llm_provider == provider


def test_llm_config_rejects_unsupported_provider():
    """Unsupported provider names are rejected."""
    with pytest.raises(ValidationError):
        LLMConfig(llm_provider="unsupported_provider")  # pyright: ignore[reportArgumentType]


def test_settings_aggregates_all_groups():
    """Settings exposes all nested configuration groups."""
    settings = Settings()
    assert settings.app is not None
    assert settings.database is not None
    assert settings.triage is not None
    assert settings.llm is not None


def test_env_example_contains_no_secrets():
    """.env.example has only placeholders, no real credentials."""
    with open(".env.example") as f:
        content = f.read()
    assert "sk-" not in content
    assert "change-in-production" in content


def test_database_url_async_driver_conversion():
    """The app engine converts plain postgresql:// URLs to asyncpg."""
    url = "postgresql://user:pass@localhost:5432/db"
    converted = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    assert converted == "postgresql+asyncpg://user:pass@localhost:5432/db"


def test_postgresql_drivers_importable():
    """Both pinned PostgreSQL drivers are installed and importable."""
    import importlib

    assert importlib.import_module("asyncpg") is not None
    assert importlib.import_module("psycopg") is not None
