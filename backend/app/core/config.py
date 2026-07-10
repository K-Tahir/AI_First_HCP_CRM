"""
Application configuration.

All configuration is sourced from environment variables (see .env.example).
Nothing is hardcoded: the LLM provider, model name, and database engine are
all swappable purely through environment configuration, per the assignment's
"configurable architecture" requirement.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, loaded once and cached."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "AIVOA AI-First CRM - HCP Module"
    APP_ENV: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero external
    # setup. In line with the assignment's MySQL requirement, set DATABASE_URL
    # to a MySQL DSN, e.g.:
    #   mysql+pymysql://user:password@localhost:3306/aivoa_crm
    DATABASE_URL: str = "sqlite:///./aivoa_crm.db"

    # --- Groq / LLM ---
    GROQ_API_KEY: str = ""
    # Groq deprecated gemma2-9b-it (Aug 2025) and, more recently, both
    # llama-3.1-8b-instant and llama-3.3-70b-versatile (Jun 2026). Defaults
    # below point at Groq's currently-recommended replacements. Swapping
    # models is purely a config change - see app/agent/llm.py.
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # --- LangGraph ---
    LANGGRAPH_RECURSION_LIMIT: int = 15

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()


settings = get_settings()
