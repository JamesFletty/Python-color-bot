"""Assemble formula steps and orchestrate the deterministic engine."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Optional, cast

from .engine_models import (
    EngineInput,
    EngineOutput,
    PersistencePayload,
    RecommendationStatus,
    RuleEvaluationContext,
    SelectedShade,
    ServiceIntent,
    SuggestedFormulaStep,
)
from .production_models import FormulaStatus, FormulaZone
from .quantity import apply_quantity_plan, quantity_rationale
from .repositories import EngineRepository
from .rule_evaluator import evaluate_and_apply_rules
from src.sub_range_intake import sub_range_labels_from_selected_shades
from .safety_checks import (
    build_risk_assessments,
    check_intermixing,
    check_lift_and_color_science,
    derive_recommendation_status,
    merge_recommendation_status,
    resolve_line_technical_defaults,
)


def _parse_time_adjustment(minutes: int, adjustments: list[str]) -> int:
    total = minutes
    for adj in adjustments:
        if adj.startswith("+") and adj.endswith("min"):
            try:
                total += int(adj[1:-3])
            except ValueError:
                continue
        elif adj.startswith("-") and adj.endswith("min"):
            try:
                total -= int(adj[1:-3])
            except ValueError:
                continue
    return max(5, total)


def _build_steps_for_intent(
    engine_input: EngineInput,
    developer_volume: int,
    processing_time: int,
    mixing_ratio: str,
    require_natural_mix: bool,
    natural_ratio: float,
) -> list[SuggestedFormulaStep]:
    shades = engine_input.selected_shades
    primary = shades[0] if shades else None

    if engine_input.service_intent == ServiceIntent.GLOSS_REFRESH:
        return [
            SuggestedFormulaStep(
                step_order=1,
                zone=FormulaZone.ALL,
                shade_id=primary.shade_id if primary else None,
                shade_code=primary.shade_code if primary else None,
                developer_id=engine_input.developer_id,
                developer_volume=10,
                mixing_ratio="1:1",
                quantity_grams=60,
                processing_time_minutes=min(processing_time, 20),
                special_instructions="Gloss refresh application.",
            )
        ]

    if engine_input.service_intent == ServiceIntent.CORRECTION:
        return []

    steps: list[SuggestedFormulaStep] = []

    if engine_input.service_intent in {ServiceIntent.LIFT_AND_TONE, ServiceIntent.GRAY_COVERAGE}:
        root_shade = next((s for s in shades if s.zone == FormulaZone.ROOT), primary)
        mid_shade = next((s for s in shades if s.zone == FormulaZone.MID), primary)
        end_shade = next((s for s in shades if s.zone == FormulaZone.END), primary)

        steps.append(
            SuggestedFormulaStep(
                step_order=1,
                zone=FormulaZone.ROOT,
                shade_id=root_shade.shade_id if root_shade else None,
                shade_code=root_shade.shade_code if root_shade else None,
                developer_id=engine_input.developer_id,
                developer_volume=developer_volume,
                mixing_ratio=mixing_ratio,
                quantity_grams=30,
                processing_time_minutes=processing_time,
                special_instructions=(
                    f"Include {natural_ratio:.0%} natural shade mix."
                    if require_natural_mix
                    else None
                ),
            )
        )
        pull_through_shade = mid_shade or end_shade
        if pull_through_shade:
            steps.append(
                SuggestedFormulaStep(
                    step_order=2,
                    zone=FormulaZone.MID,
                    shade_id=pull_through_shade.shade_id,
                    shade_code=pull_through_shade.shade_code,
                    developer_id=engine_input.developer_id,
                    developer_volume=developer_volume,
                    mixing_ratio=mixing_ratio,
                    quantity_grams=30,
                    processing_time_minutes=max(10, processing_time - 10),
                    special_instructions="Mids/ends pull-through.",
                )
            )
        return steps

    # tone_deposit default single step
    return [
        SuggestedFormulaStep(
            step_order=1,
            zone=FormulaZone.ALL,
            shade_id=primary.shade_id if primary else None,
            shade_code=primary.shade_code if primary else None,
            developer_id=engine_input.developer_id,
            developer_volume=developer_volume,
            mixing_ratio=mixing_ratio,
            quantity_grams=60,
            processing_time_minutes=processing_time,
        )
    ]


def build_persistence_payload(
    engine_input: EngineInput,
    brand_id: uuid.UUID,
    steps: list[SuggestedFormulaStep],
    risk_score: Decimal,
    total_time: int,
    explanation: str,
    risk_assessments: list,
) -> PersistencePayload:
    formula_id = uuid.uuid4()
    return PersistencePayload(
        formula={
            "formula_id": formula_id,
            "consultation_id": engine_input.consultation_id,
            "line_id": engine_input.line_id,
            "recommendation_type": engine_input.recommendation_type.value,
            "status": FormulaStatus.DRAFT.value,
            "risk_score": risk_score,
            "total_processing_time": total_time,
            "ai_explanation": explanation,
            "is_favorite": False,
        },
        formula_steps=[
            {
                "step_id": uuid.uuid4(),
                "formula_id": formula_id,
                "step_order": step.step_order,
                "zone": step.zone.value,
                "shade_id": step.shade_id,
                "developer_id": step.developer_id,
                "mixing_ratio": step.mixing_ratio,
                "quantity_grams": step.quantity_grams,
                "processing_time_minutes": step.processing_time_minutes,
                "special_instructions": step.special_instructions,
                "is_optional": step.is_optional,
            }
            for step in steps
        ],
        risk_assessments=[
            {
                "assessment_id": uuid.uuid4(),
                "formula_id": formula_id,
                "risk_type": r.risk_type.value,
                "probability": r.probability,
                "severity": r.severity.value,
                "contributing_factors": r.contributing_factors,
                "mitigation": r.mitigation,
                "requires_waiver": r.requires_waiver,
                "waiver_text": r.waiver_text,
            }
            for r in risk_assessments
        ],
    )


def run_engine(
    engine_input: EngineInput,
    repository: EngineRepository,
    *,
    line_region_id: Optional[uuid.UUID] = None,
    context_overrides: Optional[dict[str, object]] = None,
) -> EngineOutput:
    """
    Execute the deterministic formula engine end-to-end.

    Execution order:
      1. Resolve brand from line
      2. Build evaluation context
      3. Load + evaluate formulation rules
      4. Merge line technical defaults
      5. Run intermixing + color science safety checks
      6. Assemble formula steps (unless blocked / correction-only)
      7. Build risk assessments + persistence payload
    """
    brand_id = engine_input.brand_id or repository.get_brand_id_for_line(engine_input.line_id)
    region_id = line_region_id or engine_input.line_region_id
    context = RuleEvaluationContext.from_input(engine_input, brand_id)
    overrides = dict(context_overrides or {})
    if "selected_sub_ranges" not in overrides:
        labels = sub_range_labels_from_selected_shades(engine_input.selected_shades)
        if labels:
            overrides["selected_sub_ranges"] = labels
    if overrides:
        context = context.model_copy(update=overrides)

    formulation_rules = repository.load_active_formulation_rules(brand_id, engine_input.line_id)
    matched_rules, accumulated = evaluate_and_apply_rules(formulation_rules, context)

    requested_workflow = getattr(context, "workflow", None)
    if requested_workflow and requested_workflow not in accumulated.triggered_workflows:
        accumulated.triggered_workflows.append(str(requested_workflow))

    formula_zones: list[str] | None = None
    if "WF_retouch_with_refresh" in accumulated.triggered_workflows:
        formula_zones = ["root", "mid", "end"]

    line_defaults: dict[str, object] = {}
    if region_id:
        line_defaults = resolve_line_technical_defaults(
            repository.load_line_technical_rules(region_id)
        )

    developer_volume: int | None = None
    if accumulated.developer_locked:
        developer_volume = accumulated.developer_volume
    else:
        developer_default = accumulated.developer_volume or line_defaults.get("developer_volume") or 20
        developer_volume = int(cast(Any, developer_default))
    processing_default = (
        accumulated.processing_time_minutes or line_defaults.get("processing_time_minutes") or 35
    )
    processing_time = int(cast(Any, processing_default))
    processing_time = _parse_time_adjustment(
        processing_time, accumulated.processing_time_adjustments
    )
    mixing_ratio = str(
        accumulated.mixing_ratio or line_defaults.get("mixing_ratio") or "1:1"
    )

    intermix_blocks: list[str] = []
    intermix_warnings: list[str] = []
    intermix_developer_override: int | None = None
    if region_id:
        intermix_blocks, intermix_warnings, intermix_developer_override = check_intermixing(
            engine_input.selected_shades,
            repository.load_intermixing_rules(region_id),
        )
    if intermix_developer_override is not None and not accumulated.developer_locked:
        developer_volume = intermix_developer_override

    science_consultations, science_warnings = check_lift_and_color_science(
        context,
        repository.load_universal_color_science(),
        accumulated,
    )

    all_blocks = list(accumulated.hard_stops) + intermix_blocks
    all_warnings = accumulated.warnings + intermix_warnings + science_warnings
    consultations = list(science_consultations) + [
        w
        for w in accumulated.triggered_workflows
        if w in {"pre_lightening_consultation", "color_correction"}
    ]

    status = derive_recommendation_status(
        all_blocks,
        consultations,
        all_warnings,
        accumulated.triggered_workflows,
    )
    status = merge_recommendation_status(status, accumulated.recommendation_status)

    steps: list[SuggestedFormulaStep] = []
    if status not in {RecommendationStatus.BLOCKED, RecommendationStatus.REQUIRES_CONSULTATION}:
        steps = _build_steps_for_intent(
            engine_input,
            developer_volume,
            processing_time,
            mixing_ratio,
            accumulated.require_natural_shade_mix,
            accumulated.natural_shade_ratio,
        )
        if accumulated.fill_pigment_guidance:
            accumulated.fill_pigment_guidance = repository.enrich_fill_guidance(
                region_id,
                accumulated.fill_pigment_guidance,
            )
            fill = accumulated.fill_pigment_guidance
            tone_summary = ", ".join(
                step["underlying_pigment"] for step in fill.get("fill_steps", [])
            )
            fill_step = SuggestedFormulaStep(
                step_order=0,
                zone=FormulaZone.ALL,
                processing_time_minutes=max(15, processing_time - 5),
                special_instructions=(
                    f"Pre-fill / repigmentation: deposit warm tones ({tone_summary}) "
                    f"before target level {fill.get('target_level')} formula. "
                    f"Suggested fill ratio ~{int(float(fill.get('suggested_fill_ratio', 0.3)) * 100)}%."
                ),
                is_optional=False,
            )
            steps = [fill_step, *steps]
            for idx, step in enumerate(steps, start=1):
                steps[idx - 1] = step.model_copy(update={"step_order": idx})
        for idx, extra in enumerate(accumulated.extra_steps, start=len(steps) + 1):
            steps.append(extra.model_copy(update={"step_order": idx}))
        steps = apply_quantity_plan(steps, engine_input)

    risk_assessments = build_risk_assessments(accumulated, context)
    base_risk = sum(float(r.probability) for r in risk_assessments) / max(len(risk_assessments), 1)
    risk_score = Decimal(str(min(1.0, round(base_risk, 2))))

    explanation_parts = [
        f"Matched {len(matched_rules)} formulation rule(s).",
        f"Developer {developer_volume} vol, {processing_time} min processing.",
        quantity_rationale(engine_input),
    ]
    if accumulated.require_natural_shade_mix:
        explanation_parts.append(
            f"Natural shade mix required ({accumulated.natural_shade_ratio:.0%})."
        )
    if accumulated.fill_pigment_guidance:
        fill = accumulated.fill_pigment_guidance
        explanation_parts.append(
            f"Fill/repigmentation required ({fill.get('deposit_levels')} levels): "
            f"warm pigments at levels {[s['level'] for s in fill.get('fill_steps', [])]}."
        )
    if accumulated.triggered_workflows:
        explanation_parts.append(f"Workflows: {', '.join(accumulated.triggered_workflows)}.")
    explanation = " ".join(explanation_parts)

    persistence: PersistencePayload | None = None
    if steps and brand_id and status == RecommendationStatus.OK:
        persistence = build_persistence_payload(
            engine_input,
            brand_id,
            steps,
            risk_score,
            processing_time,
            explanation,
            risk_assessments,
        )

    return EngineOutput(
        recommendation_status=status,
        matched_rules=matched_rules,
        blocked_by=all_blocks,
        warnings=all_warnings,
        suggested_formula=steps,
        risk_assessments=risk_assessments,
        explanation_summary=explanation,
        persistence_payload=persistence,
        triggered_workflows=accumulated.triggered_workflows,
        formula_zones=formula_zones,
        fill_pigment_guidance=accumulated.fill_pigment_guidance,
        quantity_rationale=quantity_rationale(engine_input),
        audit_trail=[
            rule.model_dump(mode="json")
            for rule in matched_rules
            if rule.evidence_status or rule.evidence_notes
        ],
    )
