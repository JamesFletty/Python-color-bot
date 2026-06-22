"""Pydantic settings for v2 (PostgreSQL + single OpenAI-compatible LLM provider)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(default="", alias="DATABASE_URL")

    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    llm_chat_model: str = Field(default="gpt-4o-mini", alias="LLM_CHAT_MODEL")
    llm_translate_model: str = Field(default="gpt-4o-mini", alias="LLM_TRANSLATE_MODEL")

    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://localhost:8000",
        alias="CORS_ALLOW_ORIGINS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
