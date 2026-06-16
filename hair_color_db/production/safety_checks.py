"""Safety checks: intermixing, lift risk, color science, waivers."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable
from uuid import UUID

from .engine_models import (
    AccumulatedActions,
    EngineInput,
    RecommendationStatus,
    RiskAssessmentDraft,
    RuleEvaluationContext,
    SelectedShade,
)
from .production_models import FormulaZone, RiskSeverity, RiskType
from .repositories import (
    IntermixingRuleRecord,
    LineTechnicalRuleRecord,
    UniversalColorScienceRecord,
)


def check_intermixing(
    shades: list[SelectedShade],
    rules: list[IntermixingRuleRecord],
) -> tuple[list[str], list[str]]:
    """
    Enforce shade_intermixing_rule before finalizing steps.

    Returns (hard_blocks, warnings).
    """
    if len(shades) < 2:
        return [], []

    blocks: list[str] = []
    warnings: list[str] = []
    sub_ranges = {s.sub_range_id for s in shades if s.sub_range_id}

    for rule in rules:
        applies = rule.applies_to_sub_range_id
        if not applies:
            continue

        involved = applies in sub_ranges
        if not involved and rule.rule_scope == "cross_sub_range":
            # DreamAge caution when mixing DreamAge with anything else in line
            if applies in sub_ranges and len(sub_ranges) > 1:
                involved = True

        if not involved:
            continue

        if rule.rule_scope == "sub_range_isolated_from_line":
            if len(sub_ranges) > 1:
                msg = rule.restriction_note
                if rule.restriction_type == "not_mixable":
                    blocks.append(msg)
                else:
                    warnings.append(msg)

        elif rule.rule_scope == "sub_range_internal_only":
            if sub_ranges != {applies}:
                msg = rule.restriction_note
                if rule.restriction_type == "not_mixable":
                    blocks.append(msg)
                else:
                    warnings.append(msg)

        elif rule.rule_scope == "cross_sub_range":
            compat = rule.compatible_sub_range_id
            if compat and applies in sub_ranges and compat in sub_ranges:
                if rule.restriction_type == "caution":
                    warnings.append(rule.restriction_note)
            elif compat is None and len(sub_ranges) > 1:
                if rule.restriction_type == "caution":
                    warnings.append(rule.restriction_note)
                elif rule.restriction_type == "not_mixable":
                    blocks.append(rule.restriction_note)

        elif rule.rule_scope == "shade_pair":
            shade_ids = {s.shade_id for s in shades}
            if rule.shade_id in shade_ids and rule.compatible_shade_id:
                if rule.compatible_shade_id not in shade_ids:
                    if rule.restriction_type == "not_mixable":
                        blocks.append(rule.restriction_note)
                    else:
                        warnings.append(rule.restriction_note)

    return blocks, warnings


def check_lift_and_color_science(
    context: RuleEvaluationContext,
    color_science: list[UniversalColorScienceRecord],
    accumulated: AccumulatedActions,
) -> tuple[list[str], list[str]]:
    """Use universal_color_science for lift-stage realism checks."""
    warnings: list[str] = []
    consultations: list[str] = []
    science_by_level = {row.level: row for row in color_science}

    desired = context.desired_level or context.existing_level or context.natural_level
    if desired in science_by_level and context.lift_levels >= 3:
        row = science_by_level[desired]
        if row.underlying_pigment:
            warnings.append(
                f"Level {desired} exposes underlying pigment ({row.underlying_pigment}); "
                f"neutralize with {row.neutralizing_tone or 'appropriate tone'}."
            )

    if context.lift_levels > 4 and "workflow:pre_lightening_consultation" not in accumulated.hard_stops:
        consultations.append("Lift exceeds 4 levels; pre-lightening consultation required.")

    return consultations, warnings


def resolve_line_technical_defaults(
    rules: list[LineTechnicalRuleRecord],
) -> dict[str, object]:
    """Prefer typed columns; parse JSON only when typed data absent."""
    defaults: dict[str, object] = {}
    for rule in rules:
        if rule.developer_volume and "developer_volume" not in defaults:
            defaults["developer_volume"] = rule.developer_volume
        if rule.processing_time_min and "processing_time_minutes" not in defaults:
            defaults["processing_time_minutes"] = rule.processing_time_min
        if rule.mixing_ratio_num and rule.mixing_ratio_den:
            defaults["mixing_ratio"] = f"{rule.mixing_ratio_num}:{rule.mixing_ratio_den}"
        if rule.max_lift_levels is not None and "max_lift_levels" not in defaults:
            defaults["max_lift_levels"] = rule.max_lift_levels

        if rule.rule_value and isinstance(rule.rule_value, dict):
            if "developer_volume" not in defaults:
                strengths = rule.rule_value.get("strengths") or []
                for item in strengths:
                    if isinstance(item, dict) and item.get("volume"):
                        text = str(item["volume"])
                        for vol in (10, 20, 30, 40):
                            if str(vol) in text:
                                defaults["developer_volume"] = vol
                                break
            if "mixing_ratio" not in defaults:
                default_ratio = rule.rule_value.get("default")
                if isinstance(default_ratio, str) and ":" in default_ratio:
                    defaults["mixing_ratio"] = default_ratio.split()[0]
    return defaults


def build_risk_assessments(
    accumulated: AccumulatedActions,
    context: RuleEvaluationContext,
) -> list[RiskAssessmentDraft]:
    """Convert accumulated risk modifiers into risk_assessment drafts."""
    assessments: list[RiskAssessmentDraft] = []

    for risk_key, delta in accumulated.risk_modifiers.items():
        try:
            risk_type = RiskType(risk_key)
        except ValueError:
            continue
        probability = Decimal(str(min(1.0, max(0.05, abs(delta)))))
        severity = RiskSeverity.HIGH if delta >= 0.3 else RiskSeverity.MEDIUM
        assessments.append(
            RiskAssessmentDraft(
                risk_type=risk_type,
                probability=probability,
                severity=severity,
                contributing_factors=[
                    {"field": "lift_levels", "value": context.lift_levels},
                    {"field": "texture", "value": context.texture},
                ],
                mitigation=f"Monitor {risk_key} risk during processing; adjust technique accordingly.",
                requires_waiver=delta >= 0.3,
                waiver_text=(
                    f"Client acknowledges elevated {risk_key} risk."
                    if delta >= 0.3
                    else None
                ),
            )
        )

    if context.porosity > 7:
        assessments.append(
            RiskAssessmentDraft(
                risk_type=RiskType.POROSITY_MISMATCH,
                probability=Decimal("0.55"),
                severity=RiskSeverity.MEDIUM,
                contributing_factors=[{"porosity": context.porosity}],
                mitigation="Use reduced developer and shortened processing time.",
            )
        )

    return assessments


def derive_recommendation_status(
    hard_blocks: Iterable[str],
    consultations: Iterable[str],
    warnings: Iterable[str],
    workflows: Iterable[str],
) -> RecommendationStatus:
    if hard_blocks:
        return RecommendationStatus.BLOCKED
    if consultations or any(w in {"color_correction", "pre_lightening_consultation"} for w in workflows):
        return RecommendationStatus.REQUIRES_CONSULTATION
    if warnings:
        return RecommendationStatus.CAUTION
    return RecommendationStatus.OK


_STATUS_RANK = {
    RecommendationStatus.OK: 0,
    RecommendationStatus.CAUTION: 1,
    RecommendationStatus.REQUIRES_CONSULTATION: 2,
    RecommendationStatus.BLOCKED: 3,
}


def merge_recommendation_status(
    derived: RecommendationStatus,
    rule_status: RecommendationStatus | None,
) -> RecommendationStatus:
    """Take the more severe of safety-derived and rule-declared status."""
    if rule_status is None:
        return derived
    if _STATUS_RANK[rule_status] >= _STATUS_RANK[derived]:
        return rule_status
    return derived
