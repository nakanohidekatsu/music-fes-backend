from __future__ import annotations
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    APP_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        """FRONTEND_URL をカンマ区切りで複数指定可能。"""
        return [u.strip() for u in self.FRONTEND_URL.split(",") if u.strip()]

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Mail
    MAIL_FROM: str = "no-reply@example.com"
    MAIL_TO: str = "admin@example.com"
    MAIL_API_KEY: str = ""

    # Google Custom Search
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_CX: str = ""

    # SerpAPI (https://serpapi.com)
    SERPAPI_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
