"""Application settings, read from the .env file.

Nothing environment-specific is hard-coded, so the same code runs against
a local database now and a hosted one later with no edits.
"""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database ---
    # No default: the app refuses to start without it, which beats
    # starting up and failing on the first query.
    database_url: str

    # --- security ---
    # Signs login tokens. Also no default, deliberately: a fallback value
    # here would ship to production unnoticed and let anyone forge a login.
    secret_key: str
    access_token_expire_minutes: int = 60 * 24

    # --- app ---
    app_name: str = "StockEx API"
    debug: bool = False

    # Browsers refuse cross-origin requests unless the server allows them.
    # The React dev server runs on 5173 (Vite's default).
    # NoDecode matters here. Without it, pydantic-settings treats a list
    # field as complex and tries to JSON-parse the environment variable
    # BEFORE any validator runs — so a comma-separated value blows up
    # before the validator below ever sees it. NoDecode hands the raw
    # string over instead.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalise_driver(cls, value: str) -> str:
        """Force the psycopg driver onto the connection URL.

        Hosted databases hand out URLs starting `postgres://` or
        `postgresql://`. SQLAlchemy reads the scheme to pick a driver, and
        without the suffix it looks for psycopg2, which is not installed —
        so a deploy fails at startup with a confusing ImportError. Fixing
        it here means the URL can be pasted in exactly as the provider
        gives it.
        """
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        """Accept a plain comma-separated list in the environment.

        Without this, a list field has to be given as JSON — and typing
        `["https://..."]` into a hosting dashboard is easy to get wrong in
        a way that only shows up as a CORS error in the browser.
        """
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


settings = Settings()
