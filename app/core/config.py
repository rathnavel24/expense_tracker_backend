from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables (and `.env` in development)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production"] = "development"

    # Timezone that defines "today" for generating recurring transactions.
    app_timezone: str = "Asia/Kolkata"

    database_url: PostgresDsn

    # Session cookie
    session_cookie_name: str = "et_session"
    session_ttl_days: int = Field(default=30, ge=1, le=365)
    # Secure cookies require HTTPS. Must be true in production; may be false for local http dev.
    cookie_secure: bool = True

    # Only needed when the browser talks to the API directly (not through the Next.js proxy).
    cors_origins: list[str] = []

    # Login throttling: max failed attempts per email inside the window.
    login_max_failures: int = 5
    login_failure_window_minutes: int = 15

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sqlalchemy_url(self) -> str:
        # Normalise any postgres:// or postgresql:// URL to use the psycopg (v3) driver.
        url = str(self.database_url)
        scheme, rest = url.split("://", 1)
        return f"postgresql+psycopg://{rest}" if "+" not in scheme else url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
