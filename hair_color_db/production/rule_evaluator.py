"""Formulation rule condition evaluation and action accumulation."""

from __future__ import annotations

from typing import Any

from hair_color_db.formulation_rules.evaluator import (
    apply_core_rule_action,
    evaluate_condition as shared_evaluate_condition,
    evaluate_predicate,
    is_blocked_status,
    resolve_context_field,
)

from .engine_models import (
    AccumulatedActions,
    MatchedRule,
    RecommendationStatus,
    RuleEvaluationContext,
    RuleScopeTier,
    SuggestedFormulaStep,
)
from .production_models import FormulaZone
from .repositories import FormulationRuleRecord


_SCOPE_RANK = {
    RuleScopeTier.UNIVERSAL: 0,
    RuleScopeTier.BRAND: 1,
    RuleScopeTier.LINE: 2,
}


def rule_scope_tier(rule: FormulationRuleRecord) -> RuleScopeTier:
    if rule.line_ids:
        return RuleScopeTier.LINE
    if rule.brand_ids:
        return RuleScopeTier.BRAND
    return RuleScopeTier.UNIVERSAL


def evaluate_condition(
    condition: dict[str, Any], context: RuleEvaluationContext
) -> tuple[bool, str]:
    """Evaluate rule_condition JSON (delegates to shared evaluator)."""
    return shared_evaluate_condition(condition, context)


def sort_rules_for_application(
    rules: list[tuple[FormulationRuleRecord, MatchedRule]],
) -> list[tuple[FormulationRuleRecord, MatchedRule]]:
    """
    Sort matched rules for action application.

    Lower ``rule_priority`` applies earlier within the same scope tier.
    Higher scope tier (line > brand > universal) wins on scalar conflicts
      because it is applied later.
    """
    return sorted(
        rules,
        key=lambda pair: (
            _SCOPE_RANK[pair[1].scope_tier],
            pair[0].rule_priority,
        ),
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
                ),
            )
        )
    return sort_rules_for_application(matched)


def apply_rule_action(
    action: dict[str, Any], accumulated: AccumulatedActions
) -> None:
    """Apply a single rule action onto accumulated state (Stage 13 action surface)."""
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

    if risk_mod := action.get("risk_modifier"):
        accumulated.apply_risk_modifier({str(k): float(v) for k, v in risk_mod.items()})

    if risk_inc := action.get("increase_risk_score"):
        accumulated.apply_risk_modifier({str(k): float(v) for k, v in risk_inc.items()})

    if add_step := action.get("add_step"):
        zone_raw = add_step.get("zone", "all")
        zone = FormulaZone(zone_raw) if isinstance(zone_raw, str) else zone_raw
        adjustment = add_step.get("processing_time_adjustment")
        if adjustment:
            accumulated.processing_time_adjustments.append(str(adjustment))
        accumulated.extra_steps.append(
            SuggestedFormulaStep(
                step_order=0,
                zone=zone,
                processing_time_minutes=accumulated.processing_time_minutes,
                special_instructions=f"Added by rule step ({adjustment or 'no time adjustment'})",
            )
        )


def evaluate_and_apply_rules(
    rules: list[FormulationRuleRecord], context: RuleEvaluationContext
) -> tuple[list[MatchedRule], AccumulatedActions]:
    """Match rules, apply in precedence order, return audit trail + state."""
    matched_pairs = match_formulation_rules(rules, context)
    accumulated = AccumulatedActions()
    matched_rules: list[MatchedRule] = []
    for rule, meta in matched_pairs:
        apply_rule_action(rule.rule_action, accumulated)
        matched_rules.append(meta)
        if is_blocked_status(accumulated.recommendation_status):
            break
    return matched_rules, accumulated


# Re-export shared helpers used by tests and callers.
__all__ = [
    "RuleEvaluationContext",
    "apply_rule_action",
    "evaluate_and_apply_rules",
    "evaluate_condition",
    "evaluate_predicate",
    "resolve_context_field",
]
