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
    SESSION_COOKIE_NAME: str = "drevenka_session"
    SESSION_TTL_HOURS: int = 24
    # Syntetická demo hesla pouze pro vývojové a předváděcí účty (v produkci přepsat v .env)
    DEMO_MANAGER_PASSWORD: str = "drevenka2026"
    DEMO_WAREHOUSE_PASSWORD: str = "sklad2026"
    DEMO_CUSTOMER_PASSWORD: str = "zakaznik2026"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
