"""Deterministic Stage 13 formulation rule resolver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .loaders import (
    flatten_line_override_rules,
    load_decision_order,
    load_universal_rules,
    stage12_canonical_keys_with_shades,
)
from .pigment_fill import compute_fill_guidance


@dataclass
class ResolverContext:
    """Normalized intake context for rule evaluation."""

    canonical_key: str | None = None
    patch_test_status: str = "passed"
    service_intent: str = "tone_deposit"
    natural_level: int | None = None
    existing_level: int | None = None
    desired_level: int | None = None
    gray_percentage: float = 0
    porosity: int = 5
    texture: str | None = None
    pre_lightened: bool = False
    existing_artificial_color: str | None = None
    line_category: str | None = None
    selected_sub_ranges: list[str] | None = None
    workflow: str | None = None
    lift_levels: float = 0
    deposit_levels: float = 0
    level_delta: float = 0

    def as_dict(self) -> dict[str, Any]:
        """Flat dict for field lookups."""
        return {
            "canonical_key": self.canonical_key,
            "patch_test_status": self.patch_test_status,
            "service_intent": self.service_intent,
            "natural_level": self.natural_level,
            "existing_level": self.existing_level,
            "desired_level": self.desired_level,
            "gray_percentage": self.gray_percentage,
            "porosity": self.porosity,
            "texture": self.texture,
            "pre_lightened": self.pre_lightened,
            "existing_artificial_color": self.existing_artificial_color,
            "line_category": self.line_category,
            "selected_sub_ranges": self.selected_sub_ranges or [],
            "workflow": self.workflow,
            "lift_levels": self.lift_levels,
            "deposit_levels": self.deposit_levels,
            "level_delta": self.level_delta,
        }


@dataclass
class ResolverResult:
    """Output of Stage 13 rule resolution."""

    canonical_key: str | None
    recommendation_status: str = "ok"
    matched_rules: list[str] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    triggered_workflow: str | None = None
    developer_volume: int | None = None
    mixing_ratio: str | None = None
    natural_shade_ratio: float | None = None
    dormant_line: bool = False
    manual_review: bool = False
    block_reason: str | None = None
    formula_zones: list[str] | None = None
    fill_pigment_guidance: dict[str, Any] | None = None
    deposit_levels: float = 0
    _developer_locked: bool = field(default=False, repr=False)
    _require_fill_pigment: bool = field(default=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_key": self.canonical_key,
            "recommendation_status": self.recommendation_status,
            "matched_rules": self.matched_rules,
            "actions": self.actions,
            "warnings": self.warnings,
            "triggered_workflow": self.triggered_workflow,
            "developer_volume": self.developer_volume,
            "mixing_ratio": self.mixing_ratio,
            "natural_shade_ratio": self.natural_shade_ratio,
            "dormant_line": self.dormant_line,
            "manual_review": self.manual_review,
            "block_reason": self.block_reason,
            "formula_zones": self.formula_zones,
            "deposit_levels": self.deposit_levels,
            "fill_pigment_guidance": self.fill_pigment_guidance,
        }


_STATUS_RANK = {
    "ok": 0,
    "caution": 1,
    "requires_consultation": 2,
    "blocked": 3,
}


def build_context_from_intake(intake: dict[str, Any], canonical_key: str | None = None) -> ResolverContext:
    """Build resolver context from validation case input or CLI intake."""
    natural = intake.get("natural_level")
    existing = intake.get("existing_level")
    desired = intake.get("desired_level")
    base = existing if existing is not None else natural
    lift = 0.0
    deposit = 0.0
    level_delta = 0.0
    if base is not None and desired is not None:
        level_delta = float(desired) - float(base)
        lift = max(0.0, level_delta)
        deposit = max(0.0, -level_delta)

    return ResolverContext(
        canonical_key=canonical_key or intake.get("canonical_key"),
        patch_test_status=str(intake.get("patch_test_status", "passed")),
        service_intent=str(intake.get("service_intent", "tone_deposit")),
        natural_level=natural,
        existing_level=existing,
        desired_level=desired,
        gray_percentage=float(intake.get("gray_percentage", 0) or 0),
        porosity=int(intake.get("porosity", 5) or 5),
        texture=intake.get("texture"),
        pre_lightened=bool(intake.get("pre_lightened", False)),
        existing_artificial_color=intake.get("existing_artificial_color"),
        line_category=intake.get("line_category"),
        selected_sub_ranges=intake.get("selected_sub_ranges"),
        workflow=intake.get("workflow"),
        lift_levels=lift,
        deposit_levels=deposit,
        level_delta=level_delta,
    )


def _resolve_field(context: ResolverContext, field_name: str) -> Any:
    return context.as_dict().get(field_name)


def _compare(left: Any, op: str, right: Any, context: ResolverContext) -> bool:
    if op in {"exists", "is_not_null"}:
        if left is None:
            return False
        if isinstance(left, str):
            return len(left.strip()) > 0
        if isinstance(left, (list, tuple, set)):
            return len(left) > 0
        return True

    if left is None:
        return False

    if isinstance(right, str) and right in {"existing_level", "natural_level", "desired_level"}:
        right = _resolve_field(context, right)

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


def evaluate_condition(condition: dict[str, Any], context: ResolverContext) -> bool:
    """Evaluate rule_condition with all_of / any_of groups."""
    all_of = condition.get("all_of") or []
    any_of = condition.get("any_of") or []

    if all_of:
        for pred in all_of:
            left = _resolve_field(context, pred["field"])
            if not _compare(left, pred["op"], pred.get("value"), context):
                return False
    if any_of:
        if not any(
            _compare(_resolve_field(context, pred["field"]), pred["op"], pred.get("value"), context)
            for pred in any_of
        ):
            return False
    return True


def _is_dormant_canonical_key(canonical_key: str | None) -> bool:
    if not canonical_key:
        return False
    shade_keys = stage12_canonical_keys_with_shades()
    from .loaders import load_line_overrides

    for group in load_line_overrides():
        if group["canonical_key"] == canonical_key and group.get("requires_stage12_inventory_addition"):
            return canonical_key not in shade_keys
    return False


def _collect_applicable_rules(canonical_key: str | None, *, include_dormant: bool = False) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for rule in load_universal_rules():
        item = dict(rule)
        item["scope_level"] = "universal"
        rules.append(item)

    dormant = _is_dormant_canonical_key(canonical_key)
    if dormant and not include_dormant:
        return rules

    for rule in flatten_line_override_rules(include_dormant=include_dormant):
        if not canonical_key or rule.get("canonical_key") != canonical_key:
            continue
        item = dict(rule)
        item["scope_level"] = "line"
        rules.append(item)
    return rules


def _apply_action(result: ResolverResult, action: dict[str, Any], rule_id: str) -> None:
    result.actions.append({"rule_id": rule_id, **action})

    status = action.get("set_recommendation_status")
    if status:
        if _STATUS_RANK.get(status, 0) >= _STATUS_RANK.get(result.recommendation_status, 0):
            result.recommendation_status = status
        if status == "blocked":
            result.manual_review = True
        if status == "requires_consultation":
            result.manual_review = True

    if action.get("block_reason"):
        result.block_reason = str(action["block_reason"])

    if action.get("trigger_workflow"):
        result.triggered_workflow = str(action["trigger_workflow"])

    if "set_developer_volume" in action:
        volume = action.get("set_developer_volume")
        if volume is None:
            result.developer_volume = None
            result._developer_locked = True
        elif not result._developer_locked:
            result.developer_volume = volume

    if action.get("mixing_ratio"):
        result.mixing_ratio = str(action["mixing_ratio"])

    if action.get("require_natural_shade_mix"):
        ratio = action.get("natural_shade_ratio")
        if ratio is not None:
            result.natural_shade_ratio = float(ratio)

    if action.get("require_fill_pigment"):
        result._require_fill_pigment = True

    warning = action.get("warning")
    if warning:
        result.warnings.append(str(warning))


def resolve_formulation_rules(
    intake: dict[str, Any],
    *,
    canonical_key: str | None = None,
    include_dormant: bool = False,
) -> ResolverResult:
    """
    Resolve Stage 13 universal + active line override rules for an intake context.

    Dormant line override groups (requires_stage12_inventory_addition without Stage 12
    shades) are skipped unless include_dormant=True.
    """
    context = build_context_from_intake(intake, canonical_key=canonical_key)
    result = ResolverResult(canonical_key=context.canonical_key)
    result.deposit_levels = context.deposit_levels
    result.dormant_line = _is_dormant_canonical_key(context.canonical_key)

    if context.workflow:
        result.triggered_workflow = context.workflow
        if context.workflow == "WF_retouch_with_refresh":
            result.formula_zones = ["root", "mid", "end"]

    rules = _collect_applicable_rules(context.canonical_key, include_dormant=include_dormant)
    decision = load_decision_order()
    scope_rank = {"universal": 0, "brand": 1, "line": 2, "service": 3}

    matched: list[tuple[int, int, dict[str, Any]]] = []
    for rule in rules:
        if not evaluate_condition(rule.get("rule_condition", {}), context):
            continue
        scope = rule.get("scope_level", "universal")
        matched.append((scope_rank.get(scope, 99), int(rule.get("rule_priority", 100)), rule))

    matched.sort(key=lambda item: (item[0], item[1]))

    for _, _, rule in matched:
        rule_id = rule["rule_id"]
        result.matched_rules.append(rule_id)
        _apply_action(result, rule.get("rule_action", {}), rule_id)
        if result.recommendation_status == "blocked":
            break

    if result._require_fill_pigment or context.deposit_levels >= 2:
        base = context.existing_level if context.existing_level is not None else context.natural_level
        desired = context.desired_level
        if base is not None and desired is not None and int(base) > int(desired):
            result.fill_pigment_guidance = compute_fill_guidance(
                starting_level=int(base),
                target_level=int(desired),
            )

    if result.dormant_line and not include_dormant:
        result.warnings.append(
            f"Line overrides dormant for {context.canonical_key} until Stage 12 shade inventory exists."
        )

    return result
