"""
Application configuration.

All configuration is loaded from environment variables (or a .env file in
local development) via pydantic-settings. Nothing here should hardcode
secrets or environment-specific values.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "ModelWatch"
    environment: str = "local"
    debug: bool = True

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/modelwatch"

    # Redis / RQ
    redis_url: str = "redis://localhost:6379/0"

    # Auth (used starting M2, present now so .env.example is complete)
    secret_key: str = "change-me-in-production"
    api_key_prefix_length: int = 8


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we don't re-parse the environment on every call."""
    return Settings()
