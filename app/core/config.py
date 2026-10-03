"""Application settings.

Configuration is read from the .env file rather than hard-coded, so the same
code can run against a local database now and a hosted one later without
changing a single line.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # No default value: the app refuses to start if this is missing,
    # which is better than starting up and failing later.
    database_url: str

    app_name: str = "StockEx API"
    debug: bool = False


# Created once, imported everywhere. Reading the file repeatedly would be wasteful.
settings = Settings()
