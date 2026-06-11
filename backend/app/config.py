from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite by default so `uvicorn app.main:app` works with zero setup.
    # docker-compose overrides this with the Postgres URL.
    database_url: str = "sqlite+aiosqlite:///./quwwa.db"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    coaching_max_tokens: int = 8192

    # Optional: form-video search uses the official YouTube Data API when set,
    # otherwise falls back to parsing the public results page (no key needed).
    youtube_api_key: str | None = None

    # Coaching snapshots are reused for this long unless a new session is logged.
    coaching_cache_hours: int = 6

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
