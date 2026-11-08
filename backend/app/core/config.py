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
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ebay_client_id: str = ""
    ebay_client_secret: str = ""
    ebay_marketplace_id: str = "EBAY_CA"
    valuation_cache_ttl_seconds: int = 86400


settings = Settings()