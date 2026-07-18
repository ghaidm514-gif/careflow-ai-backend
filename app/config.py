"""CareFlow AI Configuration — Nested Pydantic Settings."""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    class Config:
        env_prefix = "CAREFLOW_"
        env_file = ".env"


class TriageConfig(BaseSettings):
    max_triage_questions: int = Field(default=5, ge=1, le=20)
    low_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)

    class Config:
        env_prefix = "CAREFLOW_"
        env_file = ".env"


class LLMConfig(BaseSettings):
    llm_provider: Literal["mock", "claude", "openai"] = "mock"
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_timeout_seconds: int = Field(default=30, ge=1, le=300)

    class Config:
        env_prefix = "CAREFLOW_"
        env_file = ".env"


class DatabaseConfig(BaseSettings):
    database_url: str = "sqlite:///:memory:"

    class Config:
        env_prefix = "CAREFLOW_"
        env_file = ".env"


class Settings(BaseSettings):
    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    triage: TriageConfig = TriageConfig()
    llm: LLMConfig = LLMConfig()

    class Config:
        env_file = ".env"


def load_settings() -> Settings:
    return Settings()
