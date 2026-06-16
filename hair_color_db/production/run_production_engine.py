#!/usr/bin/env python3
"""Run the production formula engine against PostgreSQL (DATABASE_URL)."""

from __future__ import annotations

import json
import sys
import uuid
from typing import Any

from hair_color_db.production.bootstrap import bootstrap_database
from hair_color_db.production.catalog_lookup import DEFAULT_SUB_RANGE, resolve_catalog_reference
from hair_color_db.production.db import create_session_factory, require_database_url
from hair_color_db.production.engine_models import EngineInput, SelectedShade, ServiceIntent
from hair_color_db.production.formula_builder import run_engine
from hair_color_db.production.persist import persist_engine_output
from hair_color_db.production.production_models import FormulaZone, HairTexture, RecommendationType
from hair_color_db.production.repositories import SqlAlchemyEngineRepository


def _parse_service_intent(raw: str) -> ServiceIntent:
    try:
        return ServiceIntent(raw)
    except ValueError as exc:
        valid = ", ".join(item.value for item in ServiceIntent)
        raise ValueError(f"Invalid service intent {raw!r}. Choose one of: {valid}") from exc


def build_engine_input_from_args(args: Any, catalog: Any) -> EngineInput:
    return EngineInput(
        consultation_id=uuid.UUID(args.consultation_id)
        if args.consultation_id
        else uuid.uuid4(),
        line_id=catalog.line_id,
        brand_id=catalog.brand_id,
        line_region_id=catalog.line_region_id,
        natural_level=args.natural_level,
        existing_level=args.existing_level,
        porosity=args.porosity,
        elasticity=args.elasticity,
        gray_percentage=args.gray_percentage,
        texture=HairTexture(args.texture),
        desired_result=args.desired_result,
        desired_level=args.desired_level,
        service_intent=_parse_service_intent(args.service_intent),
        recommendation_type=RecommendationType(args.recommendation_type),
        selected_shades=[
            SelectedShade(
                shade_id=catalog.shade_id,
                shade_code=catalog.shade_code,
                zone=FormulaZone.ALL,
            )
        ],
    )


def run_production_engine(
    session,
    engine_input: EngineInput,
    *,
    line_region_id: uuid.UUID | None = None,
    context_overrides: dict[str, object] | None = None,
    persist: bool = False,
) -> dict[str, object]:
    """Execute the engine and optionally persist the formula."""
    repo = SqlAlchemyEngineRepository(session)
    region_id = line_region_id or engine_input.line_region_id
    output = run_engine(
        engine_input,
        repo,
        line_region_id=region_id,
        context_overrides=context_overrides,
    )

    formula_id = None
    if persist:
        formula_id = persist_engine_output(session, engine_input, output)
        if formula_id is not None:
            session.commit()

    return {
        "recommendation_status": output.recommendation_status.value,
        "matched_rules": [rule.rule_id for rule in output.matched_rules],
        "matched_rule_names": [rule.rule_name for rule in output.matched_rules],
        "developer_volume": next(
            (step.developer_volume for step in output.suggested_formula if step.developer_volume),
            None,
        ),
        "warnings": output.warnings,
        "blocked_by": output.blocked_by,
        "explanation_summary": output.explanation_summary,
        "suggested_formula_steps": len(output.suggested_formula),
        "formula_id": str(formula_id) if formula_id else None,
        "persisted": formula_id is not None,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Run the production formula engine against PostgreSQL"
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Apply migrations and import Stage 12/13 before running",
    )
    parser.add_argument(
        "--canonical-key",
        default="Matrix::SoColor::US",
        help="Brand::Line::Region canonical key",
    )
    parser.add_argument("--shade-code", default="5NN", help="Target shade code")
    parser.add_argument(
        "--sub-range",
        default=None,
        help="Sub-range name for catalog lookup (default: line default sub-range)",
    )
    parser.add_argument("--natural-level", type=int, default=5)
    parser.add_argument("--existing-level", type=int, default=None)
    parser.add_argument("--desired-level", type=int, default=None)
    parser.add_argument("--gray-percentage", type=int, default=0)
    parser.add_argument("--porosity", type=int, default=5)
    parser.add_argument("--elasticity", type=int, default=6)
    parser.add_argument(
        "--texture",
        default="medium",
        choices=[item.value for item in HairTexture],
    )
    parser.add_argument("--desired-result", default="rich brunette")
    parser.add_argument(
        "--service-intent",
        default="tone_deposit",
        choices=[item.value for item in ServiceIntent],
    )
    parser.add_argument(
        "--recommendation-type",
        default="safest",
        choices=[item.value for item in RecommendationType],
    )
    parser.add_argument(
        "--consultation-id",
        default=None,
        help="Existing consultation UUID (created automatically when persisting)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write formula / steps / risk rows when status is ok",
    )
    args = parser.parse_args(argv)

    if not require_database_url(args.database_url):
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    SessionLocal = create_session_factory(database_url=args.database_url)
    with SessionLocal() as session:
        if args.bootstrap:
            bootstrap_database(session, database_url=args.database_url)
            session.commit()

        catalog = resolve_catalog_reference(
            session,
            canonical_key=args.canonical_key,
            shade_code=args.shade_code,
            sub_range_name=args.sub_range or DEFAULT_SUB_RANGE,
        )
        engine_input = build_engine_input_from_args(args, catalog)
        context_overrides: dict[str, object] = {}
        if args.sub_range:
            context_overrides["selected_sub_ranges"] = [args.sub_range]

        result = run_production_engine(
            session,
            engine_input,
            line_region_id=catalog.line_region_id,
            context_overrides=context_overrides or None,
            persist=args.persist,
        )
        print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
