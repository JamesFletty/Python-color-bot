"""Shared helpers for Stage 13 resolver vs production engine validation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from hair_color_db.stage13_formulation_rules.loaders import (
    load_line_overrides,
    load_universal_rules,
    load_validation_cases,
)
from hair_color_db.stage13_formulation_rules.resolver import ResolverResult, resolve_formulation_rules

from .engine_models import (
    AccumulatedActions,
    EngineInput,
    EngineOutput,
    MatchedRule,
    RecommendationStatus,
    RuleEvaluationContext,
    ServiceIntent,
)
from .formula_builder import run_engine
from .import_stage13_rules import LineScope, build_formulation_rules_from_stage13
from .production_models import HairTexture
from .repositories import InMemoryEngineRepository, UniversalColorScienceRecord
from .rule_evaluator import evaluate_and_apply_rules

CANONICAL_LINE_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")
DEFAULT_CANONICAL_KEY = "Matrix::SoColor::US"

# Intake fields used by Stage 13 rules but not on EngineInput.
CONTEXT_EXTRA_FIELDS = frozenset(
    {
        "patch_test_status",
        "pre_lightened",
        "line_category",
        "selected_sub_ranges",
        "workflow",
        "previous_direct_dye",
    }
)

# Cases where production elevates rule warnings to `caution` via derive_recommendation_status
# while Stage 13 leaves status `ok` when only a warning action fired.
WARNING_ELEVATION_CASES = frozenset(
    {
        "VC006_gray_blend_matrix_sync",
        "VC007_supersync_tint_back",
        "VC009_coil_gray_ratio",
        "VC010_direct_dye_no_developer",
        "VC019_wella_colortouch_soft_blend",
        "VC023_pulpriot_direct_dye",
    }
)

# Resolver-only expectations not surfaced by run_engine().
RESOLVER_ONLY_EXPECTATIONS = frozenset({"formula_zones"})


@dataclass
class CrossEngineComparison:
    case_id: str
    stage13: ResolverResult
    production: EngineOutput
    formulation_matched_package_ids: list[str]
    formulation_status: RecommendationStatus | None
    formulation_developer_volume: int | None
    formulation_mixing_ratio: str | None
    formulation_natural_shade_ratio: float | None
    formulation_block_reason: str | None
    formulation_triggered_workflow: str | None
    divergences: list[str] = field(default_factory=list)


def canonical_brand_id(canonical_key: str) -> uuid.UUID:
    brand_name = canonical_key.split("::", 1)[0]
    return uuid.uuid5(CANONICAL_LINE_NAMESPACE, f"brand:{brand_name}")


def canonical_line_id(canonical_key: str) -> uuid.UUID:
    return uuid.uuid5(CANONICAL_LINE_NAMESPACE, canonical_key)


@lru_cache(maxsize=1)
def rule_name_to_package_id() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for rule in load_universal_rules():
        mapping[str(rule["rule_name"])] = str(rule["rule_id"])
    for group in load_line_overrides():
        for rule in group.get("override_rules", []):
            mapping[str(rule["rule_name"])] = str(rule["rule_id"])
    return mapping


@lru_cache(maxsize=1)
def validation_canonical_keys() -> set[str]:
    keys: set[str] = set()
    for case in load_validation_cases():
        if case.get("canonical_key"):
            keys.add(str(case["canonical_key"]))
    for group in load_line_overrides():
        keys.add(str(group["canonical_key"]))
    return keys


def build_validation_line_mapping() -> dict[str, LineScope]:
    return {
        key: LineScope(
            brand_id=canonical_brand_id(key),
            line_id=canonical_line_id(key),
        )
        for key in validation_canonical_keys()
    }


def build_cross_engine_repository() -> InMemoryEngineRepository:
    """Repository with all validation-case line scopes mapped to Stage 13 rules."""
    line_mapping = build_validation_line_mapping()
    rules = build_formulation_rules_from_stage13(line_mapping=line_mapping)
    brand_id_by_line = {
        scope.line_id: scope.brand_id
        for scope in line_mapping.values()
        if scope.line_id and scope.brand_id
    }
    return InMemoryEngineRepository(
        brand_id_by_line=brand_id_by_line,
        formulation_rules=rules,
        line_technical_rules=[],
        intermixing_rules=[],
        color_science=[
            UniversalColorScienceRecord(
                6, "Orange", "Blue", None, "Mid lift", "established"
            ),
            UniversalColorScienceRecord(
                9, "Yellow", "Violet", None, "High lift", "established"
            ),
        ],
    )


def _parse_texture(raw: Any) -> HairTexture:
    if raw is None:
        return HairTexture.MEDIUM
    return HairTexture(str(raw))


def intake_context_extras(intake: dict[str, Any]) -> dict[str, Any]:
    return {key: intake[key] for key in CONTEXT_EXTRA_FIELDS if key in intake}


def validation_case_to_engine_input(
    case: dict[str, Any],
    *,
    consultation_id: uuid.UUID | None = None,
) -> EngineInput:
    intake = dict(case.get("input", {}))
    canonical_key = case.get("canonical_key") or DEFAULT_CANONICAL_KEY
    line_id = canonical_line_id(str(canonical_key))
    brand_id = canonical_brand_id(str(canonical_key))

    natural_level = int(intake.get("natural_level", 5))
    existing_level = intake.get("existing_level")
    desired_level = intake.get("desired_level")

    return EngineInput(
        consultation_id=consultation_id or uuid.uuid4(),
        line_id=line_id,
        brand_id=brand_id,
        natural_level=natural_level,
        existing_level=existing_level,
        desired_level=desired_level,
        existing_artificial_color=intake.get("existing_artificial_color"),
        porosity=int(intake.get("porosity", 5)),
        elasticity=int(intake.get("elasticity", 6)),
        gray_percentage=int(intake.get("gray_percentage", 0)),
        texture=_parse_texture(intake.get("texture")),
        desired_result=str(intake.get("desired_result", "validation case")),
        desired_tone=intake.get("desired_tone"),
        service_intent=ServiceIntent(str(intake.get("service_intent", "tone_deposit"))),
    )


def _package_ids_from_matched(matched_rules: list[MatchedRule]) -> list[str]:
    name_map = rule_name_to_package_id()
    return [name_map[rule.rule_name] for rule in matched_rules if rule.rule_name in name_map]


def run_formulation_layer(
    engine_input: EngineInput,
    repository: InMemoryEngineRepository,
    context_overrides: dict[str, Any],
) -> tuple[list[MatchedRule], AccumulatedActions]:
    brand_id = engine_input.brand_id or repository.get_brand_id_for_line(engine_input.line_id)
    context = RuleEvaluationContext.from_input(engine_input, brand_id)
    if context_overrides:
        context = context.model_copy(update=context_overrides)
    rules = repository.load_active_formulation_rules(brand_id, engine_input.line_id)
    return evaluate_and_apply_rules(rules, context)


def compare_validation_case(
    case: dict[str, Any],
    repository: InMemoryEngineRepository,
) -> CrossEngineComparison:
    case_id = str(case["case_id"])
    intake = dict(case.get("input", {}))
    canonical_key = case.get("canonical_key")
    extras = intake_context_extras(intake)

    stage13 = resolve_formulation_rules(intake, canonical_key=canonical_key)
    engine_input = validation_case_to_engine_input(case)
    production = run_engine(engine_input, repository, context_overrides=extras)
    matched, accumulated = run_formulation_layer(engine_input, repository, extras)

    pkg_ids = _package_ids_from_matched(matched)
    triggered = accumulated.triggered_workflows[-1] if accumulated.triggered_workflows else None

    comparison = CrossEngineComparison(
        case_id=case_id,
        stage13=stage13,
        production=production,
        formulation_matched_package_ids=pkg_ids,
        formulation_status=accumulated.recommendation_status,
        formulation_developer_volume=accumulated.developer_volume,
        formulation_mixing_ratio=accumulated.mixing_ratio,
        formulation_natural_shade_ratio=accumulated.natural_shade_ratio,
        formulation_block_reason=accumulated.block_reason,
        formulation_triggered_workflow=triggered,
    )

    expected = dict(case.get("expected", {}))
    divergences: list[str] = []

    expected_status = str(expected.get("recommendation_status", "ok"))
    actual_status = production.recommendation_status.value
    if case_id in WARNING_ELEVATION_CASES:
        if expected_status == "ok" and actual_status == "caution":
            divergences.append("warning_elevates_to_caution: accepted production behavior")
        elif expected_status != actual_status:
            divergences.append(
                f"recommendation_status: stage13={stage13.recommendation_status} "
                f"production={actual_status}"
            )
    elif expected_status != actual_status:
        divergences.append(
            f"recommendation_status: stage13={stage13.recommendation_status} "
            f"production={actual_status}"
        )

    if "matched_rules" in expected:
        expected_rules = set(str(r) for r in expected["matched_rules"])
        stage13_rules = set(stage13.matched_rules)
        prod_rules = set(pkg_ids)
        if not expected_rules.issubset(stage13_rules):
            divergences.append(
                f"stage13 matched_rules missing {sorted(expected_rules - stage13_rules)}"
            )
        if not expected_rules.issubset(prod_rules):
            divergences.append(
                f"production matched_rules missing {sorted(expected_rules - prod_rules)}"
            )

    if "developer_volume" in expected:
        expected_dev = expected["developer_volume"]
        actual_dev = accumulated.developer_volume
        if expected_dev != actual_dev:
            divergences.append(
                f"developer_volume: expected={expected_dev} formulation={actual_dev}"
            )

    if "mixing_ratio" in expected:
        if expected["mixing_ratio"] != accumulated.mixing_ratio:
            divergences.append(
                f"mixing_ratio: expected={expected['mixing_ratio']} "
                f"formulation={accumulated.mixing_ratio}"
            )

    if "natural_shade_ratio" in expected:
        if float(expected["natural_shade_ratio"]) != float(
            accumulated.natural_shade_ratio or 0
        ):
            divergences.append(
                f"natural_shade_ratio: expected={expected['natural_shade_ratio']} "
                f"formulation={accumulated.natural_shade_ratio}"
            )

    if expected_status == "blocked" and expected.get("block_reason") is None:
        if stage13.block_reason and stage13.block_reason not in production.blocked_by:
            if accumulated.block_reason not in (production.blocked_by or []):
                divergences.append("block_reason not propagated to production.blocked_by")

    if "triggered_workflow" in expected:
        expected_wf = str(expected["triggered_workflow"])
        prod_wfs = production.triggered_workflows
        if expected_wf not in prod_wfs and stage13.triggered_workflow != expected_wf:
            divergences.append(
                f"triggered_workflow: expected={expected_wf} production={prod_wfs}"
            )

    comparison.divergences = divergences
    return comparison
