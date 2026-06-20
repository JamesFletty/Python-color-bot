"""FastAPI wrapper for the SQLite and PostgreSQL formula engines."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from api.schemas import FormulaRequest, HealthResponse, AIFormulaRequest, AITranslateRequest, AIFormulaResponse
from hair_color_db.production.catalog_lookup import DEFAULT_SUB_RANGE, resolve_from_shade_reference
from hair_color_db.production.consultation_service import (
    consultation_payload,
    update_consultation_status,
)
from hair_color_db.production.db import create_session_factory, require_database_url
from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.production_models import (
    ConsultationStatus,
    FormulationRule,
    HairTexture,
    RecommendationType,
    Shade,
)
from hair_color_db.production.production_schemas import (
    ConsultationResponse,
    ConsultationUpdate,
)
from hair_color_db.production.run_production_engine import run_production_engine
from src.formula_engine_service import http_status_for_formula, run_formula_engine
from src.paths import DEFAULT_DB_PATH
from src.paths import EXPECTED_SHADE_COUNT

ConsultationStatusUpdate = ConsultationUpdate

app = FastAPI(
    title="Hair Color Formula Engine",
    description="HTTP wrapper over the SQLite and PostgreSQL formula engines.",
    version="0.2.0",
)

# ── Static frontend ───────────────────────────────────────────────────────────
_FRONTEND_DIST = Path(__file__).parent.parent / "static" / "dist"


def _db_path() -> Path:
    return Path(os.environ.get("FORMULA_DB_PATH", DEFAULT_DB_PATH))


def _engine_backend() -> str:
    return os.environ.get("ENGINE_BACKEND", "sqlite").strip().lower()


def _request_auth_context(request: Request) -> dict[str, uuid.UUID | None]:
    def _parse_uuid(header: str) -> uuid.UUID | None:
        val = request.headers.get(header)
        if val:
            try:
                return uuid.UUID(val)
            except ValueError:
                pass
        return None

    return {
        "stylist_id": _parse_uuid("X-Stylist-Id"),
        "client_id": _parse_uuid("X-Client-Id"),
        "salon_id": _parse_uuid("X-Salon-Id"),
    }


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


def _production_health() -> HealthResponse:
    return _pg_health()


# ── Catalog routes ────────────────────────────────────────────────────────────

@app.get("/api/brands")
def get_brands():
    """Return all brands and their product lines."""
    from api.catalog import get_brands_and_lines
    return get_brands_and_lines()


@app.get("/api/shades")
def get_shades(line_id: int | None = None, q: str | None = None, limit: int = 40):
    """Search shades by line and/or query string."""
    from api.catalog import search_shades
    return search_shades(line_id=line_id, query=q, limit=min(limit, 100))


# ── AI routes ─────────────────────────────────────────────────────────────────

@app.post("/api/ai/formula", response_model=AIFormulaResponse)
async def ai_formula(body: AIFormulaRequest):
    """Parse natural-language input → formula engine → AI explanation."""
    from api.ai_service import AIConfigurationError, explain_formula, get_ai_settings, parse_formula_request

    # Step 1: AI parses input into structured engine params
    try:
        parsed = await parse_formula_request(
            user_input=body.user_input,
            color_line=body.color_line,
            canonical_key=body.canonical_key,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI parsing failed: {exc}") from exc

    # Step 2: Run formula engine with parsed params
    try:
        req = FormulaRequest(
            shade=parsed.get("shade", body.color_line),
            gray=parsed.get("gray"),
            current_level=parsed.get("current_level"),
            line=parsed.get("line", body.color_line),
            service_intent=parsed.get("service_intent", "tone_deposit"),
            desired_level=parsed.get("desired_level"),
            texture=parsed.get("texture", "medium"),
            porosity=int(parsed.get("porosity", 5)),
            elasticity=int(parsed.get("elasticity", 6)),
        )
        formula = run_formula_engine(req.to_engine_request(db_path=_db_path()))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Formula engine error: {exc}") from exc

    # Step 3: AI explains the result
    try:
        explanation = await explain_formula(
            formula_result=formula,
            user_input=body.user_input,
            color_line=body.color_line,
            mode="formula",
        )
    except Exception as exc:
        explanation = f"Formula computed successfully. (AI explanation unavailable: {exc})"

    return AIFormulaResponse(
        formula=formula,
        ai_explanation=explanation,
        structured_request=parsed,
        ai_provider=get_ai_settings().provider,
        status="ok",
    )


@app.post("/api/ai/translate", response_model=AIFormulaResponse)
async def ai_translate(body: AITranslateRequest):
    """Translate a formula from one color line to another with AI."""
    from api.ai_service import AIConfigurationError, explain_formula, get_ai_settings, translate_formula

    # Step 1: AI translates formula to target line params
    try:
        parsed = await translate_formula(
            source_formula=body.source_formula,
            source_line=body.source_line,
            target_line=body.target_line,
            target_canonical_key=body.target_canonical_key,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI translation failed: {exc}") from exc

    translation_notes = parsed.pop("translation_notes", None)

    # Step 2: Run formula engine with translated params
    try:
        req = FormulaRequest(
            shade=parsed.get("shade", body.target_line),
            gray=parsed.get("gray", 0),
            current_level=parsed.get("current_level"),
            line=parsed.get("line", body.target_line),
            service_intent=parsed.get("service_intent", "tone_deposit"),
            desired_level=parsed.get("desired_level"),
            texture=parsed.get("texture", "medium"),
            porosity=int(parsed.get("porosity", 5)),
            elasticity=int(parsed.get("elasticity", 6)),
        )
        formula = run_formula_engine(req.to_engine_request(db_path=_db_path()))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Formula engine error: {exc}") from exc

    # Step 3: AI explains the translation
    try:
        explanation = await explain_formula(
            formula_result=formula,
            user_input=body.source_formula,
            color_line=body.target_line,
            mode="translate",
            translation_notes=translation_notes,
        )
    except Exception as exc:
        explanation = f"Formula translated. (AI explanation unavailable: {exc})"

    return AIFormulaResponse(
        formula=formula,
        ai_explanation=explanation,
        structured_request=parsed,
        translation_notes=translation_notes,
        ai_provider=get_ai_settings().provider,
        status="ok",
    )


# ── Legacy engine routes ──────────────────────────────────────────────────────

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


def _production_formula(body: FormulaRequest, auth_context: dict | None = None) -> dict[str, Any]:
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
                consultation_id=uuid.uuid4(),
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
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL backend unavailable") from exc


@app.post("/formula")
def build_formula_endpoint(body: FormulaRequest, request: Request):
    """Build a formula from shade reference and hair condition parameters."""
    if _engine_backend() in {"postgres", "postgresql", "pg", "production"}:
        return _production_formula(body)

    try:
        formula = run_formula_engine(body.to_engine_request(db_path=_db_path()))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status_code = http_status_for_formula(formula)
    return JSONResponse(status_code=status_code, content=formula)


@app.get("/v1/production/health", response_model=HealthResponse)
def production_health() -> HealthResponse:
    """Versioned PostgreSQL readiness contract."""
    return _production_health()


@app.post("/v1/production/formula")
def build_production_formula_endpoint(body: FormulaRequest, request: Request):
    """Versioned PostgreSQL formula contract."""
    return _production_formula(body, _request_auth_context(request))


def _update_consultation_status(
    consultation_id: uuid.UUID,
    body: ConsultationStatusUpdate,
    auth_context: dict[str, uuid.UUID | None],
) -> ConsultationResponse:
    stylist_id = auth_context.get("stylist_id")
    if stylist_id is None:
        raise HTTPException(status_code=401, detail="X-Stylist-Id is required")
    database_url = require_database_url()
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is required for PostgreSQL backend")
    try:
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            consultation = update_consultation_status(
                session,
                consultation_id=consultation_id,
                stylist_id=stylist_id,
                client_id=auth_context.get("client_id"),
                salon_id=auth_context.get("salon_id"),
                status=ConsultationStatus(body.status),
            )
            session.commit()
            return ConsultationResponse.model_validate(consultation_payload(consultation))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL backend unavailable") from exc


@app.post(
    "/v1/production/consultations/{consultation_id}/status",
    response_model=ConsultationResponse,
)
def update_production_consultation_status(
    consultation_id: uuid.UUID,
    body: ConsultationStatusUpdate,
    request: Request,
) -> ConsultationResponse:
    """Create/update consultation identity context and lifecycle status."""
    return _update_consultation_status(consultation_id, body, _request_auth_context(request))


# ── SPA catch-all — serve frontend for any non-API, non-asset path ────────────
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse({"detail": "Frontend not built yet"}, status_code=503)
else:
    @app.get("/", include_in_schema=False)
    def root():
        return JSONResponse({
            "app": "ColorSynth Formula Engine",
            "status": "api_only",
            "note": "Frontend not built. Run: cd frontend && pnpm install && pnpm build",
            "docs": "/docs",
        })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
