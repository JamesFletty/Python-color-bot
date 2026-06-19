"""Tests for SQLite CLI formula builder Stage 13 convergence."""

from __future__ import annotations

import sqlite3
import unittest

from src.formula_builder import apply_stage13_formulation_overlay, build_formula, format_developer_volume
from src.matching import lookup_shade_by_reference, parse_shade_reference
from src.paths import DEFAULT_DB_PATH


class ParseShadeReferenceTests(unittest.TestCase):
    def test_three_part_reference_extracts_line_hint(self) -> None:
        brand, line, code = parse_shade_reference("Matrix::SoColor::5N")
        self.assertEqual(brand, "Matrix")
        self.assertEqual(line, "SoColor")
        self.assertEqual(code, "5N")

    def test_two_part_reference_has_no_line_hint(self) -> None:
        brand, line, code = parse_shade_reference("Wella Professionals::7/1")
        self.assertEqual(brand, "Wella Professionals")
        self.assertIsNone(line)
        self.assertEqual(code, "7/1")


class FormatDeveloperVolumeTests(unittest.TestCase):
    def test_prefers_matching_line_option(self) -> None:
        options = [
            "10 Volume (3%) Matrix Cream Developer",
            "20 Volume (6%) Matrix Cream Developer",
            "30 Volume (9%) Matrix Cream Developer",
        ]
        self.assertEqual(
            format_developer_volume(30, options),
            "30 Volume (9%) Matrix Cream Developer",
        )

    def test_falls_back_to_volume_label(self) -> None:
        self.assertEqual(format_developer_volume(20, None), "20 vol")


@unittest.skipUnless(DEFAULT_DB_PATH.exists(), "SQLite database not initialized")
class BuildFormulaStage13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(DEFAULT_DB_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_socolor_line_hint_does_not_fall_back_to_super_sync(self) -> None:
        shade = lookup_shade_by_reference(self.conn, "Matrix::SoColor::5NN")
        self.assertIsNone(shade)

    def test_matrix_socolor_gray_coverage_uses_30_vol_developer(self) -> None:
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
        self.assertEqual(formula["status"], "caution")
        self.assertEqual(formula["shade"]["product_line"], "SoColor Pre-Bonded")
        self.assertEqual(formula["shade"]["canonical_key"], "Matrix::SoColor::US")
        self.assertEqual(formula["formulation_rules"]["developer_volume"], 30)
        self.assertIn("30", formula["formula"]["developer"])
        self.assertNotIn("stage13_developer_volume", formula["formula"])
        self.assertIn("M_SOCOLOR_001", formula["formulation_rules"]["matched_rules"])

    def test_matrix_extra_coverage_gray_uses_20_vol(self) -> None:
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
        self.assertEqual(formula["formulation_rules"]["developer_volume"], 20)
        self.assertIn("M_SOCOLOR_003", formula["formulation_rules"]["matched_rules"])

    def test_heuristic_developer_used_without_stage13_intake(self) -> None:
        formula = build_formula(
            self.conn,
            shade_ref="Matrix::SoColor::5N",
            gray_percent=60.0,
            intake=None,
        )
        self.assertEqual(formula["status"], "ok")
        self.assertNotIn("formulation_rules", formula)
        self.assertIsNotNone(formula["formula"]["developer"])


class ApplyStage13OverlayTests(unittest.TestCase):
    def test_overlay_promotes_developer_to_primary_field(self) -> None:
        class StubResult:
            developer_volume = 30
            mixing_ratio = "1:1"
            natural_shade_ratio = None
            matched_rules = ["M_SOCOLOR_001"]
            warnings: list[str] = []

        formula: dict = {
            "formula": {"developer": "10 Volume (3%) Matrix Cream Developer", "developer_rationale": []},
            "assumptions": [],
        }
        apply_stage13_formulation_overlay(
            formula,
            StubResult(),
            developer_options=["30 Volume (9%) Matrix Cream Developer"],
            heuristic_developer="10 Volume (3%) Matrix Cream Developer",
        )
        self.assertEqual(formula["formula"]["developer"], "30 Volume (9%) Matrix Cream Developer")
        self.assertTrue(formula["formula"]["developer_rationale"])


if __name__ == "__main__":
    unittest.main()
