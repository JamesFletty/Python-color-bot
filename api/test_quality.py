"""Tests for response-level formula diagnostics."""

from __future__ import annotations

import unittest

from api.quality import attach_diagnostics, build_quality_flags, build_rule_provenance_summary


class QualityDiagnosticsTests(unittest.TestCase):
    def test_flags_missing_processing_gray_and_grounding(self) -> None:
        formula = {
            "status": "caution",
            "formula": {"developer": "20 vol", "processing_time": None},
            "hair_conditions": {"gray_percent": 50},
            "confidence": "unresolved",
        }
        flags = build_quality_flags(
            formula,
            structured_request={"grounding_note": "[Engine grounding] 6N was replaced"},
        )
        self.assertTrue(flags["missing_processing_time"])
        self.assertTrue(flags["missing_gray_rule"])
        self.assertTrue(flags["fallback_shade_used"])
        self.assertTrue(flags["low_confidence_catalog_match"])
        self.assertTrue(flags["blocked_or_caution"])
        self.assertEqual(flags["severity"], "caution")

    def test_rule_provenance_summary_compacts_engine_details(self) -> None:
        formula = {
            "status": "ok",
            "shade": {
                "shade_code": "08C",
                "shade_name": "Copper Blonde",
                "brand": "Example",
                "product_line": "Permanent",
            },
            "formula": {
                "developer": "20 vol",
                "developer_rationale": ["Gray coverage rule selected 20 vol."],
                "processing_time": "35 minutes",
                "gray_coverage_guidance": "Add natural series for 50% gray.",
            },
            "hair_conditions": {"gray_percent": 50},
            "formulation_rules": {"matched_rules": ["U003"]},
            "data_gaps": ["missing manufacturer timing update"],
        }
        summary = build_rule_provenance_summary(formula)
        self.assertEqual(summary["selected_shade_source"]["shade_code"], "08C")
        self.assertEqual(summary["matched_stage13_rules"], ["U003"])
        self.assertEqual(summary["developer_source"]["developer"], "20 vol")
        self.assertEqual(summary["gray_rule_source"]["gray_percent"], 50)
        self.assertEqual(summary["data_gaps"], ["missing manufacturer timing update"])

    def test_attach_diagnostics_adds_stable_blocks(self) -> None:
        formula = {"status": "ok", "formula": {"processing_time": "20 minutes"}}
        enriched = attach_diagnostics(formula)
        self.assertIn("quality_flags", enriched)
        self.assertIn("rule_provenance", enriched)
        self.assertEqual(enriched["quality_flags"]["severity"], "ok")


if __name__ == "__main__":
    unittest.main()
