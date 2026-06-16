"""Cross-engine validation: Stage 13 resolver vs production run_engine()."""

from __future__ import annotations

import unittest

from hair_color_db.stage13_formulation_rules.loaders import load_validation_cases

from .cross_engine_validation import (
    WARNING_ELEVATION_CASES,
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
        self.assertEqual(len(self.cases), 14)

    def test_cross_engine_validation_cases(self) -> None:
        hard_pass = 0
        warning_elevation = 0

        for case in self.cases:
            comparison = compare_validation_case(case, self.repo)
            case_id = comparison.case_id
            hard_failures = [
                d
                for d in comparison.divergences
                if not d.startswith("warning_elevates_to_caution")
            ]

            with self.subTest(case_id=case_id):
                self.assertEqual(hard_failures, [], comparison.divergences)
                if case_id in WARNING_ELEVATION_CASES:
                    warning_elevation += 1
                    self.assertTrue(
                        any(d.startswith("warning_elevates_to_caution") for d in comparison.divergences)
                        or comparison.production.recommendation_status.value == "caution"
                    )
                else:
                    hard_pass += 1

        self.assertEqual(hard_pass + warning_elevation, 14)
        self.assertGreaterEqual(hard_pass, 8)
        self.assertGreaterEqual(warning_elevation, 3)

    def test_vc001_patch_test_fail_blocks_production(self) -> None:
        case = next(c for c in self.cases if c["case_id"] == "VC001_safety_patch_test_fail")
        comparison = compare_validation_case(case, self.repo)
        self.assertEqual(comparison.production.recommendation_status.value, "blocked")
        self.assertIn("U001", comparison.formulation_matched_package_ids)


if __name__ == "__main__":
    unittest.main()
