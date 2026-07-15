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
    # MySQL is the assignment-mandated database. utf8mb4 (not the older utf8)
    # is required for full Unicode support (e.g. emoji in chat messages,
    # accented HCP names) - MySQL's plain "utf8" is actually a 3-byte subset
    # and will silently reject some characters without it.
    # A local SQLite file remains available as a zero-setup fallback for
    # quick frontend-only demos - set DATABASE_URL=sqlite:///./aivoa_crm.db
    # to use it - but MySQL is what this project is built and tested against.
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/aivoa_crm?charset=utf8mb4"

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
    # Caps how many past conversational turns (each turn = one HumanMessage
    # plus everything it triggered) are sent to the LLM each call. Prevents
    # prompt size - and therefore latency/timeout risk - from growing
    # unboundedly over a long chat session. The full history still lives in
    # the LangGraph checkpoint; this only limits what's actually sent to Groq
    # each turn. Trimming always operates on whole turns, so a tool call and
    # its result are never split apart.
    LANGGRAPH_HISTORY_MAX_TURNS: int = 10

    # --- History / record search ---
    # view_interaction_history (the LangGraph tool) caps rows shown to the
    # LLM/table at this default/max, to keep a single big query from blowing
    # up prompt size or latency - large result sets are summarized instead
    # of listed row-by-row. See InteractionService.search_history().
    HISTORY_QUERY_DEFAULT_LIMIT: int = 20
    HISTORY_QUERY_MAX_LIMIT: int = 50
    # The record-browser REST endpoint (GET /interactions, used by the
    # frontend's independent Browse panel) has a separate, larger cap since
    # it never touches the LLM.
    INTERACTIONS_LIST_MAX_LIMIT: int = 200

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def redacted_database_url(self) -> str:
        """DATABASE_URL with any user:password@ credentials masked out.

        Safe to print in logs or return from a debug endpoint - used
        everywhere the connection string needs to be surfaced so the
        password is never accidentally exposed in a terminal, log file,
        or HTTP response.
        """
        import re

        return re.sub(r"//([^:]+):([^@]+)@", r"//\1:***@", self.DATABASE_URL)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()


settings = get_settings()
