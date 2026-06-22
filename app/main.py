"""FastAPI application factory (v2 scaffold — routers land in Phase 3)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ColorSynth Formula Engine",
        version="2.0.0",
        description="Professional hair-color formula engine (v2, PostgreSQL-only).",
    )
    origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "version": "2.0.0-scaffold",
            "db_ready": False,
            "note": "Phase 1 scaffold — seed + engine port in progress",
        }

    return app


app = create_app()
