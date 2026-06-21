"""Shared runtime configuration for API backend selection."""

from __future__ import annotations

import os
from pathlib import Path

from src.paths import DEFAULT_DB_PATH

_POSTGRES_BACKENDS = frozenset({"postgres", "postgresql", "pg", "production"})
_PRODUCTION_ENVS = frozenset({"production", "prod"})


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return default
    cleaned = value.strip()
    return cleaned or default


def db_path() -> Path:
    return Path(env("FORMULA_DB_PATH", str(DEFAULT_DB_PATH)) or DEFAULT_DB_PATH)


def engine_backend() -> str:
    return (env("ENGINE_BACKEND", "sqlite") or "sqlite").lower()


def uses_postgres_engine() -> bool:
    return engine_backend() in _POSTGRES_BACKENDS


def app_environment() -> str:
    return (env("ENVIRONMENT") or env("APP_ENV") or "development").lower()


def is_production_environment() -> bool:
    return app_environment() in _PRODUCTION_ENVS


def cors_origins() -> list[str]:
    raw = env("CORS_ALLOW_ORIGINS", "")
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def docs_enabled() -> bool:
    explicit = env("ENABLE_OPENAPI_DOCS")
    if explicit is not None:
        return explicit.lower() in {"1", "true", "yes", "on"}
    return not is_production_environment()
