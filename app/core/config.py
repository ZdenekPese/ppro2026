import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Základní konfigurace aplikace načítaná z prostředí nebo souboru .env."""

    PROJECT_NAME: str = "Sklad Dřevěnka s.r.o."
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    DATABASE_URL: str = (
        "postgresql+psycopg://drevenka:drevenka_secret@db:5432/drevenka_db"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
