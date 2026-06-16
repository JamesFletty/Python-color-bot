"""Shared formulation rule evaluation primitives for Stage 13 and production engines."""

from .evaluator import (
    STATUS_RANK,
    apply_core_rule_action,
    compare,
    evaluate_condition,
    evaluate_predicate,
    is_blocked_status,
    normalize_status,
    resolve_context_field,
    upgrade_recommendation_status,
)

__all__ = [
    "STATUS_RANK",
    "apply_core_rule_action",
    "compare",
    "evaluate_condition",
    "evaluate_predicate",
    "is_blocked_status",
    "normalize_status",
    "resolve_context_field",
    "upgrade_recommendation_status",
]
