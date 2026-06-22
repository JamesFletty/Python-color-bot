"""Safety and status derivation helpers (v2 simplified)."""

from __future__ import annotations

from typing import Iterable

from app.services.engine_models import AccumulatedActions, RecommendationStatus, RuleEvaluationContext


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
    if rule_status is None:
        return derived
    if _STATUS_RANK[rule_status] >= _STATUS_RANK[derived]:
        return rule_status
    return derived


def check_lift_and_color_science(context: RuleEvaluationContext) -> tuple[list[str], list[str]]:
    consultations: list[str] = []
    warnings: list[str] = []
    if context.lift_levels > 4:
        consultations.append("Lift exceeds 4 levels; pre-lightening consultation required.")
    return consultations, warnings


def apply_safety_checks(
    context: RuleEvaluationContext,
    accumulated: AccumulatedActions,
) -> RecommendationStatus:
    consultations, science_warnings = check_lift_and_color_science(context)
    all_blocks = list(accumulated.hard_stops)
    all_warnings = accumulated.warnings + science_warnings
    status = derive_recommendation_status(
        all_blocks,
        consultations,
        all_warnings,
        accumulated.triggered_workflows,
    )
    return merge_recommendation_status(status, accumulated.recommendation_status)
