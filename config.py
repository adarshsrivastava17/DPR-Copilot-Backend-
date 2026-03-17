"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


def _build_db_urls():
    """Auto-detect Render's DATABASE_URL and build async/sync URLs."""
    raw_url = os.environ.get("DATABASE_URL", "")

    if raw_url:
        # Render provides postgres:// but SQLAlchemy needs postgresql://
        sync_url = raw_url.replace("postgres://", "postgresql://", 1)
        async_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1).replace("postgresql://", "postgresql+asyncpg://", 1)
        return async_url, sync_url

    # Local dev: SQLite
    return "sqlite+aiosqlite:///./data/dpr_copilot.db", "sqlite:///./data/dpr_copilot.db"


_async_url, _sync_url = _build_db_urls()


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DPR Copilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database (auto-detects Render's DATABASE_URL, falls back to SQLite)
    DATABASE_URL: str = _async_url
    DATABASE_URL_SYNC: str = _sync_url

    # JWT Auth
    JWT_SECRET: str = "change-me-in-production-use-a-strong-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "dpr_references"

    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    REPORTS_DIR: str = "./data/reports"
    CHARTS_DIR: str = "./data/charts"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Ensure data directories exist
settings = get_settings()
for dir_path in [settings.UPLOAD_DIR, settings.REPORTS_DIR, settings.CHARTS_DIR, settings.CHROMA_PERSIST_DIR]:
    os.makedirs(dir_path, exist_ok=True)
