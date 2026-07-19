"""CareFlow AI Configuration — Nested Pydantic Settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREFLOW_", env_file=".env", extra="ignore")

    environment: Literal["development", "testing", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class TriageConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREFLOW_", env_file=".env", extra="ignore")

    max_triage_questions: int = Field(default=5, ge=1, le=20)
    low_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREFLOW_", env_file=".env", extra="ignore")

    llm_provider: Literal["mock", "claude", "openai"] = "mock"
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)


class DatabaseConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREFLOW_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./careflow_dev.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    triage: TriageConfig = Field(default_factory=TriageConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_settings() -> Settings:
    return Settings()
