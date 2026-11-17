"""Application settings, read from the .env file.

Nothing environment-specific is hard-coded, so the same code runs against
a local database now and a hosted one later with no edits.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
