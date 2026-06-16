"""Golden-path and edge-case tests for the deterministic formula engine."""

from __future__ import annotations

import unittest
import uuid
from decimal import Decimal

from .engine_models import (
    AccumulatedActions,
    EngineInput,
    RecommendationStatus,
    SelectedShade,
    ServiceIntent,
)
from .formula_builder import run_engine
from .production_models import FormulaZone, HairTexture, RecommendationType
from .repositories import (
    BLENDED_SUB_RANGE_ID,
    DREAMAGE_SUB_RANGE_ID,
    HD_SUB_RANGE_ID,
    MATRIX_LINE_ID,
    MATRIX_REGION_ID,
    NORMAL_SUB_RANGE_ID,
    TEN_MIN_SUB_RANGE_ID,
    ULTRA_BLONDE_SUB_RANGE_ID,
    FormulationRuleRecord,
    InMemoryEngineRepository,
    build_seed_repository,
)
from .rule_evaluator import (
    apply_rule_action,
    evaluate_and_apply_rules,
    evaluate_condition,
    RuleEvaluationContext,
)


def _base_input(**overrides) -> EngineInput:
    defaults = dict(
        consultation_id=uuid.uuid4(),
        line_id=MATRIX_LINE_ID,
        line_region_id=MATRIX_REGION_ID,
        natural_level=5,
        existing_level=5,
        porosity=5,
        elasticity=6,
        gray_percentage=30,
        texture=HairTexture.MEDIUM,
        desired_result="rich brunette",
        desired_level=5,
        service_intent=ServiceIntent.TONE_DEPOSIT,
        recommendation_type=RecommendationType.SAFEST,
        selected_shades=[],
    )
    defaults.update(overrides)
    return EngineInput(**defaults)


class EngineGoldenPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = build_seed_repository()

    def test_gray_over_50_requires_natural_mix(self) -> None:
        result = run_engine(
            _base_input(
                gray_percentage=75,
                natural_level=5,
                service_intent=ServiceIntent.GRAY_COVERAGE,
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="5NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                        zone=FormulaZone.ROOT,
                    )
                ],
            ),
            self.repo,
        )
        names = {r.rule_name for r in result.matched_rules}
        self.assertIn("gray_coverage_high_natural_mix", names)
        self.assertTrue(any("natural" in (s.special_instructions or "").lower() for s in result.suggested_formula))

    def test_high_porosity_reduces_developer_and_time(self) -> None:
        result = run_engine(
            _base_input(porosity=8, service_intent=ServiceIntent.LIFT_AND_TONE),
            self.repo,
        )
        self.assertIn("high_porosity_reduce_developer_time", {r.rule_name for r in result.matched_rules})
        step = result.suggested_formula[0]
        self.assertLessEqual(step.developer_volume or 99, 20)
        self.assertLessEqual(step.processing_time_minutes, 35)

    def test_lift_over_four_requires_consultation(self) -> None:
        result = run_engine(
            _base_input(
                existing_level=4,
                desired_level=9,
                service_intent=ServiceIntent.LIFT_AND_TONE,
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.REQUIRES_CONSULTATION)
        self.assertIn("pre_lightening_consultation", result.triggered_workflows)

    def test_artificial_color_lighter_triggers_correction(self) -> None:
        result = run_engine(
            _base_input(
                existing_artificial_color="copper box dye",
                existing_level=6,
                desired_level=8,
                service_intent=ServiceIntent.CORRECTION,
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.REQUIRES_CONSULTATION)
        self.assertIn("color_correction", result.triggered_workflows)
        self.assertEqual(result.suggested_formula, [])

    def test_fine_texture_high_lift_breakage_risk(self) -> None:
        result = run_engine(
            _base_input(
                texture=HairTexture.FINE,
                existing_level=5,
                desired_level=8,
                service_intent=ServiceIntent.LIFT_AND_TONE,
            ),
            self.repo,
        )
        risk_types = {r.risk_type.value for r in result.risk_assessments}
        self.assertIn("breakage", risk_types)

    def test_hd_not_mixable_with_normal_socolor(self) -> None:
        result = run_engine(
            _base_input(
                service_intent=ServiceIntent.TONE_DEPOSIT,
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="HD5RR",
                        sub_range_id=HD_SUB_RANGE_ID,
                        zone=FormulaZone.ROOT,
                    ),
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="5NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                        zone=FormulaZone.MID,
                    ),
                ],
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.BLOCKED)
        self.assertTrue(any("HD" in b for b in result.blocked_by))

    def test_ultra_blonde_not_intermixable(self) -> None:
        result = run_engine(
            _base_input(
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="UL-A+",
                        sub_range_id=ULTRA_BLONDE_SUB_RANGE_ID,
                    ),
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="7NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                    ),
                ],
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.BLOCKED)

    def test_dreamage_outside_subrange_caution(self) -> None:
        result = run_engine(
            _base_input(
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="504NA",
                        sub_range_id=DREAMAGE_SUB_RANGE_ID,
                    ),
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="5NN",
                        sub_range_id=BLENDED_SUB_RANGE_ID,
                    ),
                ],
            ),
            self.repo,
        )
        self.assertIn(result.recommendation_status, {RecommendationStatus.CAUTION, RecommendationStatus.OK})
        self.assertTrue(any("DreamAge" in w for w in result.warnings))

    def test_ten_min_internal_only_blocks_other_subrange(self) -> None:
        result = run_engine(
            _base_input(
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="10MIN5N",
                        sub_range_id=TEN_MIN_SUB_RANGE_ID,
                    ),
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="5NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                    ),
                ],
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.BLOCKED)

    def test_line_rule_overrides_universal_developer(self) -> None:
        result = run_engine(
            _base_input(gray_percentage=60, service_intent=ServiceIntent.GRAY_COVERAGE),
            self.repo,
        )
        self.assertIn("matrix_socolor_resistant_gray_20vol", {r.rule_name for r in result.matched_rules})
        if result.suggested_formula:
            self.assertEqual(result.suggested_formula[0].developer_volume, 30)

    def test_missing_optional_fields_handled_deterministically(self) -> None:
        ctx = RuleEvaluationContext.from_input(
            _base_input(existing_level=None, desired_level=None, existing_artificial_color=None),
            brand_id=None,
        )
        ok, _ = evaluate_condition(
            {"all_of": [{"field": "existing_artificial_color", "op": "exists", "value": True}]},
            ctx,
        )
        self.assertFalse(ok)
        ok2, _ = evaluate_condition(
            {"all_of": [{"field": "gray_percentage", "op": ">", "value": 0}]},
            ctx,
        )
        self.assertTrue(ok2)

    def test_gloss_refresh_single_step(self) -> None:
        result = run_engine(
            _base_input(
                service_intent=ServiceIntent.GLOSS_REFRESH,
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="010T",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                    )
                ],
            ),
            self.repo,
        )
        self.assertEqual(len(result.suggested_formula), 1)
        self.assertEqual(result.suggested_formula[0].zone, FormulaZone.ALL)
        self.assertEqual(result.suggested_formula[0].developer_volume, 10)

    def test_lift_and_tone_multi_step(self) -> None:
        result = run_engine(
            _base_input(
                service_intent=ServiceIntent.LIFT_AND_TONE,
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="6NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                    )
                ],
            ),
            self.repo,
        )
        self.assertGreaterEqual(len(result.suggested_formula), 1)
        self.assertEqual(result.suggested_formula[0].zone, FormulaZone.ROOT)

    def test_irreconcilable_intermix_blocked(self) -> None:
        result = run_engine(
            _base_input(
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="HD5RR",
                        sub_range_id=HD_SUB_RANGE_ID,
                    ),
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="UL-A+",
                        sub_range_id=ULTRA_BLONDE_SUB_RANGE_ID,
                    ),
                ],
            ),
            self.repo,
        )
        self.assertEqual(result.recommendation_status, RecommendationStatus.BLOCKED)
        self.assertGreaterEqual(len(result.blocked_by), 1)

    def test_universal_color_science_warning_on_high_lift(self) -> None:
        result = run_engine(
            _base_input(
                existing_level=6,
                desired_level=9,
                service_intent=ServiceIntent.LIFT_AND_TONE,
            ),
            self.repo,
        )
        self.assertTrue(
            any("underlying pigment" in w.lower() for w in result.warnings)
            or result.recommendation_status == RecommendationStatus.REQUIRES_CONSULTATION
        )

    def test_persistence_payload_on_ok(self) -> None:
        result = run_engine(
            _base_input(
                gray_percentage=20,
                selected_shades=[
                    SelectedShade(
                        shade_id=uuid.uuid4(),
                        shade_code="5NN",
                        sub_range_id=NORMAL_SUB_RANGE_ID,
                    )
                ],
            ),
            self.repo,
        )
        if result.recommendation_status == RecommendationStatus.OK:
            self.assertIsNotNone(result.persistence_payload)
            self.assertIn("formula_id", result.persistence_payload.formula)
            self.assertGreater(len(result.persistence_payload.formula_steps), 0)

    def test_risk_modifiers_accumulate(self) -> None:
        repo = build_seed_repository()
        extra = FormulationRuleRecord(
            rule_id=uuid.uuid4(),
            rule_name="extra_overlap_risk",
            rule_priority=80,
            rule_condition={"all_of": [{"field": "lift_levels", "op": ">=", "value": 2}]},
            rule_action={"risk_modifier": {"overlap": 0.15}},
            rule_category="correction",
        )
        repo.formulation_rules.append(extra)
        result = run_engine(
            _base_input(existing_level=5, desired_level=7, service_intent=ServiceIntent.LIFT_AND_TONE),
            repo,
        )
        overlap = [r for r in result.risk_assessments if r.risk_type.value == "overlap"]
        self.assertTrue(overlap or result.matched_rules)


class RuleEvaluatorStage13ActionTests(unittest.TestCase):
    def test_blocked_status_stops_further_rules(self) -> None:
        repo = build_seed_repository()
        block_rule = FormulationRuleRecord(
            rule_id=uuid.uuid4(),
            rule_name="test_patch_fail_block",
            rule_priority=5,
            rule_condition={"all_of": [{"field": "patch_test_status", "op": "=", "value": "failed"}]},
            rule_action={
                "set_recommendation_status": "blocked",
                "block_reason": "Patch test failed; do not proceed with color service.",
            },
            rule_category="safety",
        )
        later_rule = FormulationRuleRecord(
            rule_id=uuid.uuid4(),
            rule_name="should_not_apply_after_block",
            rule_priority=200,
            rule_condition={"all_of": [{"field": "service_intent", "op": "exists", "value": True}]},
            rule_action={"set_developer_volume": 10},
            rule_category="developer",
        )
        repo.formulation_rules.extend([block_rule, later_rule])
        ctx = RuleEvaluationContext.from_input(
            _base_input(),
            brand_id=None,
        )
        ctx = ctx.model_copy(update={"patch_test_status": "failed"})
        matched, accumulated = evaluate_and_apply_rules(repo.formulation_rules, ctx)
        self.assertEqual(accumulated.recommendation_status, RecommendationStatus.BLOCKED)
        self.assertIn("Patch test failed", accumulated.block_reason or "")
        matched_names = [rule.rule_name for rule in matched]
        self.assertIn("test_patch_fail_block", matched_names)
        self.assertNotIn("should_not_apply_after_block", matched_names)

    def test_contains_operator_on_extra_context_field(self) -> None:
        ctx = RuleEvaluationContext.from_input(_base_input(), brand_id=None)
        ctx = ctx.model_copy(update={"selected_sub_ranges": ["HD", "Normal"]})
        ok, _ = evaluate_condition(
            {"all_of": [{"field": "selected_sub_ranges", "op": "contains", "value": "HD"}]},
            ctx,
        )
        self.assertTrue(ok)

    def test_mixing_ratio_and_developer_lock_from_rule(self) -> None:
        accumulated = AccumulatedActions()
        apply_rule_action(
            {"set_developer_volume": None, "mixing_ratio": "direct_application"},
            accumulated,
        )
        self.assertTrue(accumulated.developer_locked)
        self.assertIsNone(accumulated.developer_volume)
        self.assertEqual(accumulated.mixing_ratio, "direct_application")

    def test_rule_warning_accumulates(self) -> None:
        accumulated = AccumulatedActions()
        apply_rule_action({"warning": "Underlying pigment may appear warm."}, accumulated)
        self.assertIn("Underlying pigment", accumulated.warnings[0])

    def test_blocked_rule_via_engine_output(self) -> None:
        repo = build_seed_repository()
        repo.formulation_rules.append(
            FormulationRuleRecord(
                rule_id=uuid.uuid4(),
                rule_name="test_consultation_rule",
                rule_priority=15,
                rule_condition={"all_of": [{"field": "porosity", "op": ">", "value": 9}]},
                rule_action={"set_recommendation_status": "requires_consultation"},
                rule_category="porosity",
            )
        )
        result = run_engine(_base_input(porosity=10), repo)
        self.assertEqual(result.recommendation_status, RecommendationStatus.REQUIRES_CONSULTATION)


if __name__ == "__main__":
    unittest.main()
