"""Centralized runtime configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    app_name: str = "EarthPulse API"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database / cache
    database_url: str = "postgresql+asyncpg://localhost/earthpulse"
    redis_url: str = "redis://localhost:6379/0"

    # External API keys (fill via .env)
    airnow_api_key: str | None = None
    firms_map_key: str | None = None
    openaq_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
