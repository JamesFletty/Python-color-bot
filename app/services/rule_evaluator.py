"""Formulation rule condition evaluation and action accumulation (v2)."""

from __future__ import annotations

from typing import Any

from app.domain.pigment_fill import compute_fill_guidance
from app.domain.rule_evaluator_core import (
    apply_core_rule_action,
    is_blocked_status,
)
from app.domain.rule_evaluator_core import (
    evaluate_condition as shared_evaluate_condition,
)
from app.services.engine_models import (
    AccumulatedActions,
    MatchedRule,
    RecommendationStatus,
    RuleEvaluationContext,
    RuleScopeTier,
)
from app.services.repository import FormulationRuleRecord

_SCOPE_RANK = {
    RuleScopeTier.UNIVERSAL: 0,
    RuleScopeTier.BRAND: 1,
    RuleScopeTier.LINE: 2,
}


def rule_scope_tier(rule: FormulationRuleRecord) -> RuleScopeTier:
    if rule.line_id is not None:
        return RuleScopeTier.LINE
    return RuleScopeTier.UNIVERSAL


def evaluate_condition(
    condition: dict[str, Any], context: RuleEvaluationContext
) -> tuple[bool, str]:
    return shared_evaluate_condition(condition, context)


def sort_rules_for_application(
    rules: list[tuple[FormulationRuleRecord, MatchedRule]],
) -> list[tuple[FormulationRuleRecord, MatchedRule]]:
    return sorted(
        rules,
        key=lambda pair: (_SCOPE_RANK[pair[1].scope_tier], pair[0].rule_priority),
    )


def match_formulation_rules(
    rules: list[FormulationRuleRecord], context: RuleEvaluationContext
) -> list[tuple[FormulationRuleRecord, MatchedRule]]:
    matched: list[tuple[FormulationRuleRecord, MatchedRule]] = []
    for rule in rules:
        ok, reason = evaluate_condition(rule.rule_condition, context)
        if not ok:
            continue
        tier = rule_scope_tier(rule)
        matched.append(
            (
                rule,
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    rule_priority=rule.rule_priority,
                    rule_category=rule.rule_category,
                    scope_tier=tier,
                    reason=reason,
                    evidence_status=rule.evidence_status,
                ),
            )
        )
    return sort_rules_for_application(matched)


def apply_rule_action(action: dict[str, Any], accumulated: AccumulatedActions) -> None:
    apply_core_rule_action(action, accumulated, status_type=RecommendationStatus)

    if block_reason := action.get("block_reason"):
        accumulated.hard_stops.append(str(block_reason))

    if delta := action.get("adjust_developer_volume_delta"):
        if not accumulated.developer_locked:
            base = accumulated.developer_volume or 20
            accumulated.developer_volume = max(10, base + int(delta))

    if time_delta := action.get("adjust_processing_time_minutes"):
        accumulated.processing_time_minutes = max(
            5, accumulated.processing_time_minutes + int(time_delta)
        )

    if action.get("require_fill_pigment"):
        accumulated.require_fill_pigment = True

    if dev := action.get("set_developer_volume"):
        accumulated.developer_volume = int(dev)
        accumulated.developer_locked = True

    if ratio := action.get("set_mixing_ratio"):
        accumulated.mixing_ratio = str(ratio)

    if guidance := action.get("gray_coverage_guidance"):
        accumulated.gray_coverage_guidance = str(guidance)

    if rationale := action.get("developer_rationale"):
        accumulated.developer_rationale = str(rationale)


def evaluate_and_apply_rules(
    rules: list[FormulationRuleRecord], context: RuleEvaluationContext
) -> tuple[list[MatchedRule], AccumulatedActions]:
    matched_pairs = match_formulation_rules(rules, context)
    accumulated = AccumulatedActions()
    accumulated.deposit_levels = int(context.deposit_levels)
    matched_rules: list[MatchedRule] = []

    for rule, meta in matched_pairs:
        apply_rule_action(rule.rule_action, accumulated)
        matched_rules.append(meta)
        if is_blocked_status(accumulated.recommendation_status):
            break

    if accumulated.require_fill_pigment or context.deposit_levels >= 2:
        base = context.existing_level if context.existing_level is not None else context.natural_level
        desired = context.desired_level
        if desired is not None and base is not None and base > desired:
            accumulated.fill_pigment_guidance = compute_fill_guidance(
                starting_level=int(base),
                target_level=int(desired),
            )

    return matched_rules, accumulated
