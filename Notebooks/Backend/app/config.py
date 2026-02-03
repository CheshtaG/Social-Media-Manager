"""App configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the reel script generator. Reads from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    # gemini-2.5-flash-lite: higher free-tier limit (~1000 RPD). Override with GEMINI_MODEL in .env if needed.
    gemini_model: str = "gemini-2.5-flash-lite"


def get_settings() -> Settings:
    """Return app settings. Use as a FastAPI dependency."""
    return Settings()
