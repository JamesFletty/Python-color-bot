"""Route formula requests to the SQLite or PostgreSQL engine."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from api.backend import db_path, uses_postgres_engine
from api.schemas import FormulaRequest
from hair_color_db.production.catalog_lookup import DEFAULT_SUB_RANGE, resolve_from_shade_reference
from hair_color_db.production.db import create_session_factory, require_database_url
from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.production_models import HairTexture, RecommendationType
from hair_color_db.production.run_production_engine import run_production_engine
from src.formula_engine_service import run_formula_engine


def run_formula_request(
    body: FormulaRequest,
    *,
    auth_context: dict[str, uuid.UUID | None] | None = None,
) -> dict[str, Any]:
    """Execute a formula request against the configured backend."""
    if uses_postgres_engine():
        return _run_postgres_formula(body, auth_context=auth_context)
    return run_formula_engine(body.to_engine_request(db_path=db_path()))


def _run_postgres_formula(
    body: FormulaRequest,
    *,
    auth_context: dict[str, uuid.UUID | None] | None = None,
) -> dict[str, Any]:
    database_url = require_database_url()
    if not database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is required for PostgreSQL backend")

    auth_context = auth_context or {}
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
                stylist_id=auth_context.get("stylist_id"),
                client_id=auth_context.get("client_id"),
                salon_id=auth_context.get("salon_id"),
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL backend unavailable") from exc
