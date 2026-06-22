"""Rule evaluator unit tests (v2)."""

from __future__ import annotations

import unittest
import uuid

from app.services.engine_models import RuleEvaluationContext
from app.services.repository import FormulationRuleRecord
from app.services.rule_evaluator import evaluate_and_apply_rules, evaluate_condition


def _context(**overrides) -> RuleEvaluationContext:
    defaults = dict(
        consultation_id=uuid.uuid4(),
        line_id=1,
        brand_id=1,
        natural_level=5,
        existing_level=5,
        porosity=5,
        elasticity=6,
        gray_percentage=30,
        texture="medium",
        desired_result="test",
        desired_level=5,
        service_intent="gray_coverage",
        deposit_levels=0,
        lift_levels=0,
        level_delta=0,
    )
    defaults.update(overrides)
    return RuleEvaluationContext(**defaults)


class RuleEvaluatorTests(unittest.TestCase):
    def test_patch_test_fail_blocks(self) -> None:
        rule = FormulationRuleRecord(
            rule_id="U001",
            rule_name="patch_test_fail_blocks_service",
            rule_priority=10,
            rule_condition={"all_of": [{"field": "patch_test_status", "op": "=", "value": "failed"}]},
            rule_action={
                "set_recommendation_status": "blocked",
                "block_reason": "Patch test failed; do not proceed with color service.",
            },
            rule_category="safety",
        )
        ctx = _context()
        ctx = ctx.model_copy(update={"patch_test_status": "failed"})
        ok, _ = evaluate_condition(rule.rule_condition, ctx)
        self.assertTrue(ok)
        matched, accumulated = evaluate_and_apply_rules([rule], ctx)
        self.assertEqual(len(matched), 1)
        self.assertIn("Patch test failed", accumulated.hard_stops[0])

    def test_gray_coverage_rule_from_seed_shape(self) -> None:
        rule = FormulationRuleRecord(
            rule_id="M_SOCOLOR_001",
            rule_name="matrix_socolor_resistant_gray_20vol",
            rule_priority=55,
            rule_condition={"all_of": [{"field": "gray_percentage", "op": ">=", "value": 50}]},
            rule_action={"set_developer_volume": 30},
            rule_category="gray_coverage",
            line_id=1,
            scope_level="line",
        )
        matched, accumulated = evaluate_and_apply_rules(
            [rule], _context(gray_percentage=75)
        )
        self.assertEqual(len(matched), 1)
        self.assertEqual(accumulated.developer_volume, 30)

    def test_unmatched_rule_skipped(self) -> None:
        rule = FormulationRuleRecord(
            rule_id="X",
            rule_name="never_matches",
            rule_priority=1,
            rule_condition={"all_of": [{"field": "gray_percentage", "op": "=", "value": 999}]},
            rule_action={"set_developer_volume": 40},
            rule_category="test",
        )
        matched, accumulated = evaluate_and_apply_rules([rule], _context())
        self.assertEqual(len(matched), 0)
        self.assertIsNone(accumulated.developer_volume)


if __name__ == "__main__":
    unittest.main()
