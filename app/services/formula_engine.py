"""Core deterministic formula orchestration (v2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.formula import (
    FormulaBlock,
    FormulaRequest,
    FormulaResponse,
    HairConditions,
    ShadeDetail,
)
from app.services.engine_models import RuleEvaluationContext
from app.services.fill_shade import enrich_fill_guidance
from app.services.repository import EngineRepository
from app.services.rule_evaluator import evaluate_and_apply_rules
from app.services.safety import apply_safety_checks
from app.services.shade_matcher import ShadeNotFoundError, resolve_shade


def _map_status(status) -> str:
    value = status.value if hasattr(status, "value") else str(status)
    if value == "requires_consultation":
        return "caution"
    return value


def _format_processing_time(minutes: int) -> str:
    return f"{minutes} min"


def build_formula(request: FormulaRequest, db: Session) -> FormulaResponse:
    shade = resolve_shade(db, request.shade, line_hint=request.line_hint)
    repo = EngineRepository(db)
    brand_id = repo.get_brand_id_for_line(shade.line_id)

    conditions = HairConditions(
        natural_level=request.current_level,
        desired_level=request.desired_level,
        gray_percent=request.gray_percent,
        porosity=request.porosity,
        elasticity=request.elasticity,
        texture=request.texture,
    )

    context = RuleEvaluationContext.from_request(
        line_id=shade.line_id,
        brand_id=brand_id,
        natural_level=int(request.current_level) if request.current_level else None,
        existing_level=int(request.current_level) if request.current_level else None,
        desired_level=int(request.desired_level) if request.desired_level else None,
        gray_percent=request.gray_percent,
        porosity=request.porosity,
        elasticity=request.elasticity,
        texture=request.texture,
        service_intent=request.service_intent,
        sub_range=request.sub_range or shade.sub_range,
    )

    rules = repo.load_active_formulation_rules(brand_id, shade.line_id)
    matched_rules, accumulated = evaluate_and_apply_rules(rules, context)
    status = apply_safety_checks(context, accumulated)
    line_defaults = repo.get_line_technical_defaults(shade.line_id)

    if accumulated.hard_stops:
        return FormulaResponse(
            status="blocked",
            shade=ShadeDetail(
                shade_id=shade.shade_id,
                shade_code=shade.shade_code,
                shade_name=shade.shade_name,
                level=shade.level,
                brand=shade.brand,
                product_line=shade.product_line,
                canonical_key=shade.canonical_key,
                normalized_tones=shade.normalized_tones,
                sub_range=shade.sub_range,
            ),
            formula=FormulaBlock(
                developer="n/a",
                mixing_ratio="n/a",
                processing_time="n/a",
            ),
            hair_conditions=conditions,
            warnings=list(accumulated.hard_stops),
            assumptions=[],
            matched_rules=[rule.rule_name for rule in matched_rules],
        )

    developer_volume = accumulated.developer_volume or line_defaults.get("developer_volume") or 20
    processing_time = (
        accumulated.processing_time_minutes
        if accumulated.processing_time_adjustments
        else line_defaults.get("processing_time_minutes") or accumulated.processing_time_minutes
    )
    mixing_ratio = (
        accumulated.mixing_ratio
        or shade.mixing_ratio
        or line_defaults.get("mixing_ratio")
        or "1:1"
    )

    fill_guidance = accumulated.fill_pigment_guidance
    if fill_guidance:
        fill_guidance = enrich_fill_guidance(db, shade.canonical_key, fill_guidance)

    warnings = list(accumulated.warnings)
    if accumulated.require_natural_shade_mix:
        ratio_pct = int(accumulated.natural_shade_ratio * 100)
        warnings.append(f"Include {ratio_pct}% natural shade mix for gray coverage.")

    response_status = _map_status(status)
    if warnings and response_status == "ok":
        response_status = "caution"

    return FormulaResponse(
        status=response_status,
        shade=ShadeDetail(
            shade_id=shade.shade_id,
            shade_code=shade.shade_code,
            shade_name=shade.shade_name,
            level=shade.level,
            brand=shade.brand,
            product_line=shade.product_line,
            canonical_key=shade.canonical_key,
            normalized_tones=shade.normalized_tones,
            sub_range=shade.sub_range,
        ),
        formula=FormulaBlock(
            developer=f"{developer_volume} vol",
            developer_rationale=accumulated.developer_rationale,
            mixing_ratio=str(mixing_ratio).split()[0] if ":" in str(mixing_ratio) else str(mixing_ratio),
            processing_time=_format_processing_time(processing_time),
            gray_coverage_guidance=accumulated.gray_coverage_guidance,
            fill_pigment_guidance=fill_guidance,
        ),
        hair_conditions=conditions,
        warnings=warnings,
        assumptions=[
            "Stage 12 line technical defaults fill developer, ratio, and timing only when rules or shade records do not provide them."
        ],
        matched_rules=[rule.rule_name for rule in matched_rules],
    )


__all__ = ["ShadeNotFoundError", "build_formula"]
