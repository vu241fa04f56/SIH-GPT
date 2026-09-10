"""
config.py
─────────
Centralised settings loaded from environment variables / .env file.
All other modules import from here — never read os.environ directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://weathergpt:password@localhost:5432/weathergpt"
    SYNC_DATABASE_URL: str = "postgresql://weathergpt:password@localhost:5432/weathergpt"

    # ── App ──────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    API_SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Gemini ────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # ── Open-Meteo ───────────────────────────────────────────────────────────
    OPEN_METEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    OPEN_METEO_AIR_QUALITY_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_MARINE_URL: str = "https://marine-api.open-meteo.com/v1/marine"
    OPEN_METEO_ELEVATION_URL: str = "https://api.open-meteo.com/v1/elevation"

    # ── Firebase ─────────────────────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "./infra/firebase-service-account.json"

    # ── Google Cloud ─────────────────────────────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_CLOUD_PROJECT: str = ""

    # ── Model Registry ───────────────────────────────────────────────────────
    MODEL_REGISTRY_PATH: str = "./models"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            import json
            v = v.strip()
            if not v:
                return []
            # Try JSON array first (e.g. '["http://localhost:5173"]')
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Fall back to comma-separated string
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
