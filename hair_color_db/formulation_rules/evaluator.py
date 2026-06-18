"""Canonical rule condition evaluation and core action application."""

from __future__ import annotations

from enum import Enum
from typing import Any


STATUS_RANK: dict[str, int] = {
    "ok": 0,
    "caution": 1,
    "requires_consultation": 2,
    "blocked": 3,
}

_DYNAMIC_FIELD_REFERENCES = frozenset({"existing_level", "natural_level", "desired_level"})


def normalize_status(status: Any) -> str:
    """Coerce enum or string recommendation status to a lowercase string key."""
    if status is None:
        return "ok"
    if isinstance(status, Enum):
        return str(status.value)
    return str(status)


def upgrade_recommendation_status(current: Any, new: str) -> str:
    """Return the higher-severity status per ``STATUS_RANK``."""
    cur = normalize_status(current)
    if STATUS_RANK.get(new, 0) >= STATUS_RANK.get(cur, 0):
        return new
    return cur


def is_blocked_status(status: Any) -> bool:
    return normalize_status(status) == "blocked"


def resolve_context_field(context: Any, field: str) -> Any:
    """Resolve a field from dict-like or attribute-based evaluation contexts."""
    if hasattr(context, "as_dict") and callable(context.as_dict):
        return context.as_dict().get(field)

    if hasattr(context, field):
        return getattr(context, field)

    extra = getattr(context, "model_extra", None)
    if extra is not None:
        return extra.get(field)

    return None


def compare(left: Any, op: str, right: Any, context: Any) -> bool:
    """Evaluate a single predicate comparison operator."""
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

    if isinstance(right, str) and right in _DYNAMIC_FIELD_REFERENCES:
        right = resolve_context_field(context, right)

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


def evaluate_predicate(predicate: dict[str, Any], context: Any) -> bool:
    """Evaluate one ``all_of`` / ``any_of`` predicate against *context*."""
    field = predicate["field"]
    op = predicate["op"]
    value = predicate.get("value")
    left = resolve_context_field(context, field)
    return compare(left, op, value, context)


def evaluate_condition(condition: dict[str, Any], context: Any) -> tuple[bool, str]:
    """
    Evaluate ``rule_condition`` JSON.

    Returns ``(passed, reason)``. Unconditional rules (empty groups) pass.
    """
    all_of = condition.get("all_of") or []
    any_of = condition.get("any_of") or []

    if all_of:
        for pred in all_of:
            if not evaluate_predicate(pred, context):
                return (
                    False,
                    f"failed all_of: {pred['field']} {pred['op']} {pred.get('value')}",
                )
    if any_of:
        if not any(evaluate_predicate(pred, context) for pred in any_of):
            return False, "failed any_of group"
    return True, "conditions satisfied"


def apply_core_rule_action(
    action: dict[str, Any],
    target: Any,
    *,
    status_type: type | None = None,
) -> None:
    """Apply Stage 13 core rule actions onto a mutable target object."""
    status = action.get("set_recommendation_status")
    if status:
        upgraded = upgrade_recommendation_status(
            getattr(target, "recommendation_status", None), str(status)
        )
        if status_type is not None:
            target.recommendation_status = status_type(upgraded)
        else:
            target.recommendation_status = upgraded
        if upgraded in {"blocked", "requires_consultation"} and hasattr(target, "manual_review"):
            target.manual_review = True

    if block_reason := action.get("block_reason"):
        target.block_reason = str(block_reason)

    if "set_developer_volume" in action:
        volume = action.get("set_developer_volume")
        developer_locked = getattr(target, "developer_locked", getattr(target, "_developer_locked", False))
        lock_developer = bool(action.get("lock_developer_volume"))
        if volume is None:
            target.developer_volume = None
            lock_developer = True
        elif not developer_locked:
            target.developer_volume = int(volume)

        if lock_developer:
            if hasattr(target, "developer_locked"):
                target.developer_locked = True
            if hasattr(target, "_developer_locked"):
                target._developer_locked = True

    if action.get("require_natural_shade_mix"):
        if hasattr(target, "require_natural_shade_mix"):
            target.require_natural_shade_mix = True
        ratio = action.get("natural_shade_ratio")
        if ratio is not None:
            target.natural_shade_ratio = float(ratio)

    if mixing_ratio := action.get("mixing_ratio"):
        target.mixing_ratio = str(mixing_ratio)

    if workflow := action.get("trigger_workflow"):
        wf = str(workflow)
        if hasattr(target, "triggered_workflows"):
            if wf not in target.triggered_workflows:
                target.triggered_workflows.append(wf)
        elif hasattr(target, "triggered_workflow"):
            target.triggered_workflow = wf

    if warning := action.get("warning"):
        target.warnings.append(str(warning))
