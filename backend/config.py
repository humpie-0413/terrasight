"""Centralized runtime configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    app_name: str = "EarthPulse API"
    debug: bool = False  # set DEBUG=true in .env for local dev
    # Comma-separated origins; pydantic-settings parses JSON list or bare string.
    # Example env value: '["https://earthpulse.pages.dev","http://localhost:5173"]'
    cors_origins: list[str] = ["http://localhost:5173"]

    # Database / cache (not yet wired — placeholders for Phase 2)
    database_url: str = "postgresql+asyncpg://localhost/earthpulse"
    redis_url: str = "redis://localhost:6379/0"

    # ── External API keys (set via .env or platform env vars) ────────────────

    # P0 — active in current build
    airnow_api_key: str | None = None       # AirNow — Block 1 current AQI
    firms_map_key: str | None = None        # NASA FIRMS — fire hotspots globe
    openaq_api_key: str | None = None       # OpenAQ v3 — air monitors globe

    # P1 — connectors stubbed; keys needed when connectors are implemented
    epa_aqs_email: str | None = None        # EPA AQS — annual PM2.5/ozone trend
    epa_aqs_key: str | None = None          # EPA AQS — paired with email above
    cams_ads_key: str | None = None         # Copernicus ADS — smoke/AOD layer


@lru_cache
def get_settings() -> Settings:
    return Settings()
