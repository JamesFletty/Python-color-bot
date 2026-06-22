"""FastAPI application factory (v2 scaffold — routers land in Phase 3)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.config import get_settings
from app.db import get_session_factory
from app.models import FormulationRule, Shade


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
    def health() -> dict[str, object]:
        db_ready = False
        shade_count = 0
        rule_count = 0
        if settings.database_url:
            try:
                session = get_session_factory()()
                try:
                    shade_count = session.scalar(select(func.count()).select_from(Shade)) or 0
                    rule_count = session.scalar(
                        select(func.count()).select_from(FormulationRule)
                    ) or 0
                    db_ready = shade_count > 0
                finally:
                    session.close()
            except Exception:
                db_ready = False

        return {
            "status": "ok",
            "version": "2.0.0",
            "db_ready": db_ready,
            "shade_count": shade_count,
            "rule_count": rule_count,
        }

    return app


app = create_app()
