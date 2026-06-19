"""FastAPI wrapper for the SQLite and PostgreSQL formula engines."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from api.schemas import FormulaRequest, HealthResponse
from hair_color_db.production.catalog_lookup import DEFAULT_SUB_RANGE, resolve_from_shade_reference
from hair_color_db.production.db import create_session_factory, require_database_url
from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.production_models import (
    FormulationRule,
    HairTexture,
    RecommendationType,
    Shade,
)
from hair_color_db.production.run_production_engine import run_production_engine
from src.formula_engine_service import http_status_for_formula, run_formula_engine
from src.paths import DEFAULT_DB_PATH
from src.paths import EXPECTED_SHADE_COUNT

app = FastAPI(
    title="Hair Color Formula Engine",
    description="HTTP wrapper over the SQLite and PostgreSQL formula engines.",
    version="0.1.0",
)


def _db_path() -> Path:
    return Path(os.environ.get("FORMULA_DB_PATH", DEFAULT_DB_PATH))


def _engine_backend() -> str:
    return os.environ.get("ENGINE_BACKEND", "sqlite").strip().lower()


def _pg_health() -> HealthResponse:
    database_url = require_database_url()
    if not database_url:
        return HealthResponse(
            status="degraded",
            backend="postgres",
            database_path="DATABASE_URL",
            database_ready=False,
            database_url_configured=False,
            pg_db_connected=False,
            stage12_ready=False,
            stage13_ready=False,
        )

    try:
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            shade_count = int(session.scalar(select(func.count()).select_from(Shade)) or 0)
            rule_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(FormulationRule)
                    .where(FormulationRule.is_active.is_(True))
                )
                or 0
            )
    except SQLAlchemyError:
        return HealthResponse(
            status="degraded",
            backend="postgres",
            database_path="DATABASE_URL",
            database_ready=False,
            database_url_configured=True,
            pg_db_connected=False,
            stage12_ready=False,
            stage13_ready=False,
        )

    stage12_ready = shade_count >= EXPECTED_SHADE_COUNT
    stage13_ready = rule_count > 0
    ready = stage12_ready and stage13_ready
    return HealthResponse(
        status="ok" if ready else "degraded",
        backend="postgres",
        database_path="DATABASE_URL",
        database_ready=ready,
        database_url_configured=True,
        pg_db_connected=True,
        stage12_shade_count=shade_count,
        stage12_ready=stage12_ready,
        stage13_rule_count=rule_count,
        stage13_ready=stage13_ready,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if _engine_backend() in {"postgres", "postgresql", "pg", "production"}:
        return _pg_health()

    db = _db_path()
    ready = db.exists()
    return HealthResponse(
        status="ok" if ready else "degraded",
        backend="sqlite",
        database_path=str(db),
        database_ready=ready,
    )


def _production_formula(body: FormulaRequest) -> dict[str, Any]:
    database_url = require_database_url()
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is required for PostgreSQL backend")

    try:
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            catalog = resolve_from_shade_reference(
                session,
                body.shade,
                product_line_hint=body.line,
            )
            sub_range_name = (
                body.sub_ranges[0] if body.sub_ranges else catalog.sub_range_name or DEFAULT_SUB_RANGE
            )
            engine_input = EngineInput(
                consultation_id=body.consultation_id or uuid.uuid4(),
                line_id=catalog.line_id,
                brand_id=catalog.brand_id,
                line_region_id=catalog.line_region_id,
                natural_level=int(body.current_level or body.desired_level or 5),
                existing_level=int(body.existing_level) if body.existing_level is not None else None,
                porosity=body.porosity,
                elasticity=body.elasticity,
                gray_percentage=int(body.gray or 0),
                texture=HairTexture(body.texture),
                desired_result=body.desired_result,
                desired_level=int(body.desired_level) if body.desired_level is not None else None,
                service_intent=ServiceIntent(body.service_intent),
                recommendation_type=RecommendationType(body.recommendation_type),
                hair_length=body.hair_length,
                selected_shades=[
                    SelectedShade(
                        shade_id=catalog.shade_id,
                        shade_code=catalog.shade_code,
                        sub_range_name=sub_range_name,
                    )
                ],
            )
            context_overrides: dict[str, object] = {}
            if body.sub_ranges:
                context_overrides["selected_sub_ranges"] = list(body.sub_ranges)
            return run_production_engine(
                session,
                engine_input,
                line_region_id=catalog.line_region_id,
                context_overrides=context_overrides or None,
                persist=body.persist,
                stylist_id=body.stylist_id,
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL backend unavailable") from exc


@app.post("/formula")
def build_formula_endpoint(body: FormulaRequest):
    """Build a formula from shade reference and hair condition parameters."""
    if _engine_backend() in {"postgres", "postgresql", "pg", "production"}:
        return _production_formula(body)

    try:
        formula = run_formula_engine(body.to_engine_request(db_path=_db_path()))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status_code = http_status_for_formula(formula)
    return JSONResponse(status_code=status_code, content=formula)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
