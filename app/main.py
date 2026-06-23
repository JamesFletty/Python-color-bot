"""FastAPI application factory (v2)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from app.config import get_settings
from app.db import get_session_factory
from app.models import FormulationRule, Shade
from app.routers import ai, catalog, formula

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static" / "dist"


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

    app.include_router(catalog.router)
    app.include_router(formula.router)
    app.include_router(ai.router)

    @app.get("/health")
    def health() -> dict[str, object]:
        db_ready = False
        shade_count = 0
        rule_count = 0
        if settings.database_url:
            try:
                session = get_session_factory()()
                try:
                    session.execute(text("SELECT 1"))
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
            "status": "ok" if db_ready else "degraded",
            "version": "2.0.0",
            "db_ready": db_ready,
            "shade_count": shade_count,
            "rule_count": rule_count,
            "llm_configured": bool(settings.llm_api_key),
        }

    if _FRONTEND_DIST.exists():
        assets_dir = _FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        def spa_index() -> FileResponse:
            return FileResponse(str(_FRONTEND_DIST / "index.html"))

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            index = _FRONTEND_DIST / "index.html"
            if index.exists():
                return FileResponse(str(index))
            return JSONResponse({"detail": "Frontend not built"}, status_code=503)

    return app


app = create_app()
