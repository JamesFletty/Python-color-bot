"""Tests for auto sub-range intake helpers."""

from __future__ import annotations

import sqlite3
import unittest

from src.formula_builder import build_formula
from src.paths import DEFAULT_DB_PATH
from src.sub_range_intake import (
    merge_intake_sub_ranges,
    sub_range_labels_from_shade,
)


class SubRangeIntakeUnitTests(unittest.TestCase):
    def test_generic_labels_are_ignored(self) -> None:
        self.assertEqual(sub_range_labels_from_shade(""), [])
        self.assertEqual(sub_range_labels_from_shade("Standard"), [])
        self.assertEqual(sub_range_labels_from_shade("Default"), [])

    def test_collection_labels_are_kept(self) -> None:
        self.assertEqual(sub_range_labels_from_shade("Extra Coverage"), ["Extra Coverage"])
        self.assertEqual(sub_range_labels_from_shade("DreamAge"), ["DreamAge"])

    def test_explicit_intake_wins_over_shade(self) -> None:
        intake = {"selected_sub_ranges": ["HD"]}
        merged = merge_intake_sub_ranges(intake, shade_sub_range="Extra Coverage")
        self.assertEqual(merged["selected_sub_ranges"], ["HD"])

    def test_shade_sub_range_injected_when_missing(self) -> None:
        merged = merge_intake_sub_ranges(
            {"service_intent": "gray_coverage"},
            shade_sub_range="Extra Coverage",
        )
        self.assertEqual(merged["selected_sub_ranges"], ["Extra Coverage"])


@unittest.skipUnless(DEFAULT_DB_PATH.exists(), "SQLite database not initialized")
class SubRangeAutoDetectIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(DEFAULT_DB_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_matrix_extra_coverage_auto_detects_20_vol(self) -> None:
        formula = build_formula(
            self.conn,
            shade_ref="Matrix::SoColor::504N",
            gray_percent=60.0,
            intake={
                "service_intent": "gray_coverage",
                "patch_test_status": "passed",
                "porosity": 5,
                "natural_level": 5,
                "desired_level": 5,
            },
        )
        self.assertEqual(formula["status"], "caution")
        self.assertEqual(formula["shade"]["sub_range"], "Extra Coverage")
        self.assertEqual(formula["formulation_rules"]["developer_volume"], 20)
        self.assertIn("M_SOCOLOR_003", formula["formulation_rules"]["matched_rules"])

    def test_standard_sub_range_does_not_activate_collection_rules(self) -> None:
        formula = build_formula(
            self.conn,
            shade_ref="Matrix::SoColor::5N",
            gray_percent=60.0,
            intake={
                "service_intent": "gray_coverage",
                "patch_test_status": "passed",
                "porosity": 5,
            },
        )
        self.assertIn(formula["shade"]["sub_range"], ("", None))
        self.assertEqual(formula["formulation_rules"]["developer_volume"], 30)
        self.assertIn("M_SOCOLOR_001", formula["formulation_rules"]["matched_rules"])


if __name__ == "__main__":
    unittest.main()
