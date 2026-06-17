#!/usr/bin/env python3
"""Regression tests for Stage 13 validation cases (F_validation_cases.json)."""

from __future__ import annotations

import unittest

from hair_color_db.stage13_formulation_rules.loaders import clear_caches, load_validation_cases
from hair_color_db.stage13_formulation_rules.resolver import resolve_formulation_rules


class Stage13ValidationCaseTests(unittest.TestCase):
    """Run packaged validation cases against the Stage 13 resolver."""

    @classmethod
    def setUpClass(cls) -> None:
        clear_caches()

    def _assert_case(self, case: dict) -> None:
        case_id = case["case_id"]
        intake = dict(case.get("input", {}))
        canonical_key = case.get("canonical_key")
        result = resolve_formulation_rules(intake, canonical_key=canonical_key)
        expected = case.get("expected", {})

        self.assertEqual(
            result.recommendation_status,
            expected.get("recommendation_status", "ok"),
            f"{case_id}: recommendation_status",
        )

        if "matched_rules" in expected:
            self.assertTrue(
                set(expected["matched_rules"]).issubset(set(result.matched_rules)),
                f"{case_id}: expected {expected['matched_rules']} as subset of {result.matched_rules}",
            )

        if "triggered_workflow" in expected:
            self.assertEqual(result.triggered_workflow, expected["triggered_workflow"], case_id)

        if "formula_zones" in expected:
            self.assertEqual(result.formula_zones, expected["formula_zones"], case_id)

        if "developer_volume" in expected:
            self.assertEqual(result.developer_volume, expected["developer_volume"], case_id)

        if "mixing_ratio" in expected:
            self.assertEqual(result.mixing_ratio, expected["mixing_ratio"], case_id)

        if "natural_shade_ratio" in expected:
            self.assertEqual(result.natural_shade_ratio, expected["natural_shade_ratio"], case_id)

        if expected.get("dormant_line"):
            self.assertTrue(result.dormant_line, f"{case_id}: expected dormant_line")

        if expected.get("requires_stage12_inventory_addition"):
            self.assertTrue(result.dormant_line, f"{case_id}: dormant inventory flag")

    def test_all_packaged_validation_cases(self) -> None:
        cases = load_validation_cases()
        self.assertEqual(len(cases), 20)
        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self._assert_case(case)


class Stage13LiftDeveloperEscalationTests(unittest.TestCase):
    """Universal lift -> developer escalation applies even without a line rule."""

    @classmethod
    def setUpClass(cls) -> None:
        clear_caches()

    def _developer_for_lift(self, base: int, desired: int, canonical_key=None) -> int | None:
        intake = {
            "service_intent": "lift_and_tone",
            "natural_level": base,
            "existing_level": base,
            "desired_level": desired,
            "gray_percentage": 0,
            "porosity": 5,
        }
        return resolve_formulation_rules(intake, canonical_key=canonical_key).developer_volume

    def test_one_level_lift_uses_20vol(self) -> None:
        self.assertEqual(self._developer_for_lift(5, 6), 20)

    def test_two_level_lift_uses_20vol(self) -> None:
        self.assertEqual(self._developer_for_lift(5, 7), 20)

    def test_three_level_lift_uses_30vol(self) -> None:
        # Brand without a line-specific lift rule still escalates past deposit 10 vol.
        self.assertEqual(
            self._developer_for_lift(3, 6, canonical_key="L'Oréal Professionnel::Majirel::US"),
            30,
        )

    def test_four_level_lift_uses_40vol(self) -> None:
        self.assertEqual(self._developer_for_lift(3, 7), 40)

    def test_no_lift_keeps_deposit_default(self) -> None:
        # Same level (no lift) must not escalate beyond the universal 10 vol default.
        self.assertEqual(self._developer_for_lift(6, 6), 10)


class Stage13ActiveLineTests(unittest.TestCase):
    """Line overrides activate once Stage 12 shade inventory exists."""

    def test_supersync_hd_block_with_active_inventory(self) -> None:
        intake = {
            "selected_sub_ranges": ["HD", "Standard"],
            "service_intent": "tone_deposit",
        }
        result = resolve_formulation_rules(
            intake, canonical_key="Matrix::Super Sync::US", include_dormant=False
        )
        self.assertFalse(result.dormant_line)
        self.assertEqual(result.recommendation_status, "blocked")
        self.assertIn("M_SSYNC_002", result.matched_rules)


if __name__ == "__main__":
    unittest.main()
