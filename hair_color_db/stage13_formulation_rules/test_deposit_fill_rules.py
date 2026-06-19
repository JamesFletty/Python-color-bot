#!/usr/bin/env python3
"""Tests for deposit-only developer and fill pigment formulation rules."""

from __future__ import annotations

import sqlite3
import unittest

from hair_color_db.stage13_formulation_rules.loaders import clear_caches
from hair_color_db.stage13_formulation_rules.pigment_fill import compute_fill_guidance
from hair_color_db.stage13_formulation_rules.resolver import resolve_formulation_rules
from src.formula_builder import build_formula
from src.paths import DEFAULT_DB_PATH


class PigmentFillTests(unittest.TestCase):
    def test_nine_to_five_fill_steps(self) -> None:
        guidance = compute_fill_guidance(starting_level=9, target_level=5)
        self.assertEqual(guidance["deposit_levels"], 4)
        levels = [step["level"] for step in guidance["fill_steps"]]
        self.assertEqual(levels, [8, 7, 6])
        pigments = [step["underlying_pigment"] for step in guidance["fill_steps"]]
        self.assertIn("Yellow-orange", pigments)
        self.assertIn("Orange", pigments)
        self.assertEqual(guidance["target_underlying_pigment"], "Red-orange")


class DepositFillRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        clear_caches()

    def test_gray_over_fifty_defaults_to_20_vol(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "gray_coverage",
                "gray_percentage": 55,
                "natural_level": 6,
                "desired_level": 6,
            },
            canonical_key="Wella Professionals::Koleston Perfect::US",
        )
        self.assertIn("U013", result.matched_rules)
        self.assertEqual(result.developer_volume, 20)

    def test_matrix_socolor_gray_still_uses_line_30_vol_override(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "gray_coverage",
                "gray_percentage": 60,
                "natural_level": 5,
                "desired_level": 5,
            },
            canonical_key="Matrix::SoColor::US",
        )
        self.assertIn("U013", result.matched_rules)
        self.assertIn("M_SOCOLOR_001", result.matched_rules)
        self.assertEqual(result.developer_volume, 30)


    def test_multi_level_lift_developer_takes_precedence_over_line_gray_default(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "lift_and_tone",
                "gray_percentage": 60,
                "natural_level": 5,
                "desired_level": 8,
            },
            canonical_key="Wella Professionals::Koleston Perfect::US",
        )
        self.assertIn("U018", result.matched_rules)
        self.assertIn("W_KP_GRAY_001", result.matched_rules)
        self.assertEqual(result.developer_volume, 40)
        self.assertEqual(result.recommendation_status, "caution")

    def test_darken_one_level_uses_deposit_10_vol(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "tone_deposit",
                "existing_level": 8,
                "desired_level": 7,
            },
            canonical_key="Wella Professionals::Koleston Perfect::US",
        )
        self.assertIn("U014", result.matched_rules)
        self.assertEqual(result.developer_volume, 10)

    def test_multi_level_darken_requires_fill_pigment(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "tone_deposit",
                "existing_level": 9,
                "desired_level": 5,
            },
            canonical_key="Matrix::SoColor::US",
        )
        self.assertIn("U015", result.matched_rules)
        self.assertEqual(result.developer_volume, 10)
        self.assertEqual(result.triggered_workflow, "repigmentation_fill")
        self.assertIsNotNone(result.fill_pigment_guidance)
        self.assertEqual(result.fill_pigment_guidance["deposit_levels"], 4)

    def test_shades_eq_darken_uses_5_vol_demi(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "tone_deposit",
                "existing_level": 8,
                "desired_level": 6,
            },
            canonical_key="Redken::Shades EQ Gloss::US",
        )
        self.assertIn("R_SEQ_003", result.matched_rules)
        self.assertEqual(result.developer_volume, 5)


@unittest.skipUnless(DEFAULT_DB_PATH.exists(), "SQLite database not initialized")
class BuildFormulaDepositTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(DEFAULT_DB_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_cli_darken_includes_fill_guidance(self) -> None:
        formula = build_formula(
            self.conn,
            shade_ref="Matrix::SoColor::5N",
            intake={
                "service_intent": "tone_deposit",
                "existing_level": 9,
                "desired_level": 5,
                "patch_test_status": "passed",
                "porosity": 5,
            },
        )
        self.assertEqual(formula["status"], "ok")
        self.assertEqual(formula["formula"]["developer"], "10 vol")
        fill = formula["formula"]["fill_pigment_guidance"]
        self.assertIn("fill_steps", fill)
        self.assertTrue(fill["fill_steps"][0].get("suggested_shades"))
        self.assertTrue(fill.get("target_natural_shades"))

    def test_koleston_gray_uses_20_vol_with_natural_mix(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "gray_coverage",
                "gray_percentage": 55,
                "natural_level": 6,
                "desired_level": 6,
            },
            canonical_key="Wella Professionals::Koleston Perfect::US",
        )
        self.assertIn("W_KP_GRAY_001", result.matched_rules)
        self.assertEqual(result.developer_volume, 20)
        self.assertEqual(result.natural_shade_ratio, 0.5)

    def test_topchic_gray_uses_20_vol(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "gray_coverage",
                "gray_percentage": 60,
                "natural_level": 5,
                "desired_level": 5,
            },
            canonical_key="Goldwell::Topchic::US",
        )
        self.assertIn("GW_TOP_001", result.matched_rules)
        self.assertEqual(result.developer_volume, 20)

    def test_igora_absolutes_gray_uses_30_vol(self) -> None:
        result = resolve_formulation_rules(
            {
                "service_intent": "gray_coverage",
                "gray_percentage": 70,
                "natural_level": 6,
                "desired_level": 6,
                "selected_sub_ranges": ["ABSOLUTES"],
            },
            canonical_key="Schwarzkopf Professional::IGORA ROYAL::US",
        )
        self.assertIn("SK_IGORA_002", result.matched_rules)
        self.assertEqual(result.developer_volume, 30)


if __name__ == "__main__":
    unittest.main()
