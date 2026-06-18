"""Cross-engine validation: Stage 13 resolver vs production run_engine()."""

from __future__ import annotations

import unittest

from hair_color_db.stage13_formulation_rules.loaders import load_validation_cases

from .cross_engine_validation import (
    build_cross_engine_repository,
    compare_validation_case,
)


class CrossEngineValidationTests(unittest.TestCase):
    """Run F_validation_cases.json against both engines."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = build_cross_engine_repository()
        cls.cases = load_validation_cases()

    def test_packaged_case_count(self) -> None:
        self.assertEqual(len(self.cases), 20)

    def test_cross_engine_validation_cases(self) -> None:
        for case in self.cases:
            comparison = compare_validation_case(case, self.repo)
            with self.subTest(case_id=comparison.case_id):
                self.assertEqual(comparison.divergences, [])


    def test_multi_level_lift_developer_takes_precedence_over_line_gray_default(self) -> None:
        case = {
            "case_id": "lift_gray_precedence",
            "canonical_key": "Wella Professionals::Koleston Perfect::US",
            "input": {
                "service_intent": "lift_and_tone",
                "gray_percentage": 60,
                "natural_level": 5,
                "desired_level": 8,
            },
            "expected": {
                "recommendation_status": "caution",
                "matched_rules": ["U018", "W_KP_GRAY_001"],
                "developer_volume": 40,
            },
        }
        comparison = compare_validation_case(case, self.repo)
        self.assertEqual(comparison.formulation_developer_volume, 40)
        self.assertEqual(comparison.stage13.developer_volume, 40)

    def test_vc001_patch_test_fail_blocks_production(self) -> None:
        case = next(c for c in self.cases if c["case_id"] == "VC001_safety_patch_test_fail")
        comparison = compare_validation_case(case, self.repo)
        self.assertEqual(comparison.production.recommendation_status.value, "blocked")
        self.assertIn("U001", comparison.formulation_matched_package_ids)


if __name__ == "__main__":
    unittest.main()
