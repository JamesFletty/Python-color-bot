"""Formulation rule condition evaluation and action accumulation."""

from __future__ import annotations

from typing import Any

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

_STATUS_RANK = {
    RecommendationStatus.OK: 0,
    RecommendationStatus.CAUTION: 1,
    RecommendationStatus.REQUIRES_CONSULTATION: 2,
    RecommendationStatus.BLOCKED: 3,
}


def rule_scope_tier(rule: FormulationRuleRecord) -> RuleScopeTier:
    if rule.line_ids:
        return RuleScopeTier.LINE
    if rule.brand_ids:
        return RuleScopeTier.BRAND
    return RuleScopeTier.UNIVERSAL


def resolve_field_value(context: RuleEvaluationContext, field: str) -> Any:
    """Resolve a field from context; missing optional fields return None."""
    if hasattr(context, field):
        return getattr(context, field)
    extra = getattr(context, "model_extra", None) or {}
    return extra.get(field)


def _compare(left: Any, op: str, right: Any, context: RuleEvaluationContext) -> bool:
    """Evaluate a single predicate. Missing left values fail comparisons except exists."""
    if op in {"exists", "is_not_null"}:
        if left is None:
            return False
        if isinstance(left, str):
            return len(left.strip()) > 0
        if isinstance(left, (list, tuple, set)):
            return len(left) > 0
        return True

    if op == "not_exists":
        return left is None or (isinstance(left, str) and not left.strip())

    if left is None:
        return False

    if isinstance(right, str) and right in {
        "existing_level",
        "natural_level",
        "desired_level",
    }:
        right = resolve_field_value(context, right)

    if op == "=":
        return left == right
    if op == "!=":
        return left != right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == "in":
        return left in right
    if op == "not_in":
        return left not in right
    if op == "contains":
        if isinstance(left, (list, tuple, set)):
            return right in left
        if isinstance(left, str):
            return str(right) in left
        return False

    raise ValueError(f"Unsupported operator: {op}")


def evaluate_predicate(
    predicate: dict[str, Any], context: RuleEvaluationContext
) -> bool:
    field = predicate["field"]
    op = predicate["op"]
    value = predicate.get("value")
    left = resolve_field_value(context, field)
    return _compare(left, op, value, context)


def evaluate_condition(
    condition: dict[str, Any], context: RuleEvaluationContext
) -> tuple[bool, str]:
    """
    Evaluate rule_condition JSON.

  Missing-field behavior:
    - `all_of`: every predicate must pass; any missing-field failure => False
    - `any_of`: empty list => True; otherwise at least one predicate passes
    - both empty => True (unconditional rule)
    """
    all_of = condition.get("all_of") or []
    any_of = condition.get("any_of") or []

    if all_of:
        for pred in all_of:
            if not evaluate_predicate(pred, context):
                return False, f"failed all_of: {pred['field']} {pred['op']} {pred.get('value')}"
    if any_of:
        if not any(evaluate_predicate(pred, context) for pred in any_of):
            return False, "failed any_of group"
    return True, "conditions satisfied"


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
    status = action.get("set_recommendation_status")
    if status:
        new_status = RecommendationStatus(status)
        current = accumulated.recommendation_status or RecommendationStatus.OK
        if _STATUS_RANK[new_status] >= _STATUS_RANK[current]:
            accumulated.recommendation_status = new_status

    if block_reason := action.get("block_reason"):
        accumulated.block_reason = str(block_reason)
        accumulated.hard_stops.append(str(block_reason))

    if "set_developer_volume" in action:
        volume = action.get("set_developer_volume")
        if volume is None:
            accumulated.developer_volume = None
            accumulated.developer_locked = True
        elif not accumulated.developer_locked:
            accumulated.developer_volume = int(volume)

    if action.get("require_natural_shade_mix"):
        accumulated.require_natural_shade_mix = True
        accumulated.natural_shade_ratio = float(action.get("natural_shade_ratio", 0.5))

    if delta := action.get("adjust_developer_volume_delta"):
        if not accumulated.developer_locked:
            base = accumulated.developer_volume or 20
            accumulated.developer_volume = max(10, base + int(delta))

    if time_delta := action.get("adjust_processing_time_minutes"):
        accumulated.processing_time_minutes = max(
            5, accumulated.processing_time_minutes + int(time_delta)
        )

    if workflow := action.get("trigger_workflow"):
        accumulated.triggered_workflows.append(str(workflow))

    if risk_mod := action.get("risk_modifier"):
        accumulated.apply_risk_modifier({str(k): float(v) for k, v in risk_mod.items()})

    if risk_inc := action.get("increase_risk_score"):
        accumulated.apply_risk_modifier({str(k): float(v) for k, v in risk_inc.items()})

    if mixing_ratio := action.get("mixing_ratio"):
        accumulated.mixing_ratio = str(mixing_ratio)

    if warning := action.get("warning"):
        accumulated.warnings.append(str(warning))

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
        if accumulated.recommendation_status == RecommendationStatus.BLOCKED:
            break
    return matched_rules, accumulated
