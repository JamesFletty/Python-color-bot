"""Assemble formula steps and orchestrate the deterministic engine."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

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
from .repositories import EngineRepository
from .rule_evaluator import evaluate_and_apply_rules
from .safety_checks import (
    build_risk_assessments,
    check_intermixing,
    check_lift_and_color_science,
    derive_recommendation_status,
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
        if mid_shade or end_shade:
            steps.append(
                SuggestedFormulaStep(
                    step_order=2,
                    zone=FormulaZone.MID,
                    shade_id=(mid_shade or end_shade).shade_id if (mid_shade or end_shade) else None,
                    shade_code=(mid_shade or end_shade).shade_code if (mid_shade or end_shade) else None,
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

    formulation_rules = repository.load_active_formulation_rules(brand_id, engine_input.line_id)
    matched_rules, accumulated = evaluate_and_apply_rules(formulation_rules, context)

    line_defaults: dict[str, object] = {}
    if region_id:
        line_defaults = resolve_line_technical_defaults(
            repository.load_line_technical_rules(region_id)
        )

    developer_volume = int(
        accumulated.developer_volume or line_defaults.get("developer_volume") or 20
    )
    processing_time = int(
        accumulated.processing_time_minutes or line_defaults.get("processing_time_minutes") or 35
    )
    processing_time = _parse_time_adjustment(
        processing_time, accumulated.processing_time_adjustments
    )
    mixing_ratio = str(line_defaults.get("mixing_ratio") or "1:1")

    intermix_blocks: list[str] = []
    intermix_warnings: list[str] = []
    if region_id:
        intermix_blocks, intermix_warnings = check_intermixing(
            engine_input.selected_shades,
            repository.load_intermixing_rules(region_id),
        )

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
        for idx, extra in enumerate(accumulated.extra_steps, start=len(steps) + 1):
            steps.append(extra.model_copy(update={"step_order": idx}))

    risk_assessments = build_risk_assessments(accumulated, context)
    base_risk = sum(float(r.probability) for r in risk_assessments) / max(len(risk_assessments), 1)
    risk_score = Decimal(str(min(1.0, round(base_risk, 2))))

    explanation_parts = [
        f"Matched {len(matched_rules)} formulation rule(s).",
        f"Developer {developer_volume} vol, {processing_time} min processing.",
    ]
    if accumulated.require_natural_shade_mix:
        explanation_parts.append(
            f"Natural shade mix required ({accumulated.natural_shade_ratio:.0%})."
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
    )
