"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DPR Copilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database (SQLite default for local dev, PostgreSQL for production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/dpr_copilot.db"
    DATABASE_URL_SYNC: str = "sqlite:///./data/dpr_copilot.db"

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
