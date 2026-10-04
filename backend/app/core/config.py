from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at backend/app/core/config.py
BACKEND_DIR = Path(__file__).resolve().parents[2]   # .../backend
ROOT_DIR = BACKEND_DIR.parent                       # .../AuctionTracker (repo root)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AuctionTracker"
    database_url: str = "postgresql+asyncpg://auction:auction@localhost:5433/auction"


settings = Settings()