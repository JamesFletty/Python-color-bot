"""Tests for Stage 13 → production import pipeline."""

from __future__ import annotations

import unittest
import uuid

from hair_color_db.production.import_stage13_rules import (
    DictCanonicalKeyResolver,
    build_formulation_rules_from_stage13,
    build_stage13_import_rows,
    deterministic_rule_id,
    import_rows_to_formulation_rule_records,
    LineScope,
)
from hair_color_db.stage13_formulation_rules.loaders import (
    load_line_overrides,
    load_service_workflows,
    load_universal_rules,
    load_validation_cases,
)


class Stage13ImportRowTests(unittest.TestCase):
    def test_universal_rule_count(self) -> None:
        rows = build_stage13_import_rows()
        universal = [r for r in rows if r.scope_level == "universal"]
        self.assertEqual(len(universal), 18)
        self.assertEqual(len(load_universal_rules()), 18)

    def test_line_override_groups_and_rules(self) -> None:
        rows = build_stage13_import_rows()
        line_rows = [r for r in rows if r.scope_level == "line"]
        self.assertEqual(len(load_line_overrides()), 16)
        self.assertEqual(len(line_rows), 42)

    def test_matrix_socolor_resistant_gray_imports_30_vol(self) -> None:
        rows = build_stage13_import_rows()
        rule = next(r for r in rows if r.package_rule_id == "M_SOCOLOR_001")
        self.assertEqual(rule.rule_name, "matrix_socolor_resistant_gray_20vol")
        self.assertEqual(rule.rule_action.get("set_developer_volume"), 30)

    def test_dormant_groups_flagged_when_no_stage12_shades(self) -> None:
        rows = build_stage13_import_rows()
        dormant_keys = {
            r.canonical_key
            for r in rows
            if r.is_dormant and r.canonical_key
        }
        for group in load_line_overrides():
            if group.get("requires_stage12_inventory_addition"):
                key = str(group["canonical_key"])
                has_shades = any(
                    r.canonical_key == key and not r.is_dormant for r in rows
                )
                if not has_shades:
                    self.assertIn(key, dormant_keys)

    def test_deterministic_rule_ids_are_stable(self) -> None:
        first = deterministic_rule_id("U001")
        second = deterministic_rule_id("U001")
        self.assertEqual(first, second)
        self.assertNotEqual(deterministic_rule_id("U001"), deterministic_rule_id("U002"))

    def test_line_scope_attached_via_resolver(self) -> None:
        matrix_brand = uuid.UUID("00000000-0000-4000-8000-000000000001")
        matrix_line = uuid.UUID("00000000-0000-4000-8000-000000000010")
        resolver = DictCanonicalKeyResolver(
            mapping={
                "Matrix::SoColor::US": LineScope(
                    brand_id=matrix_brand, line_id=matrix_line
                ),
            }
        )
        rows = build_stage13_import_rows(resolver=resolver)
        socolor = next(r for r in rows if r.package_rule_id == "M_SOCOLOR_001")
        self.assertEqual(socolor.line_id, matrix_line)
        self.assertEqual(socolor.brand_id, matrix_brand)

    def test_build_seed_formulation_rules_include_universals_and_matrix_line(self) -> None:
        matrix_brand = uuid.UUID("00000000-0000-4000-8000-000000000001")
        matrix_line = uuid.UUID("00000000-0000-4000-8000-000000000010")
        records = build_formulation_rules_from_stage13(
            line_mapping={
                "Matrix::SoColor::US": LineScope(
                    brand_id=matrix_brand, line_id=matrix_line
                ),
            }
        )
        names = {r.rule_name for r in records}
        self.assertIn("patch_test_fail_blocks_service", names)
        self.assertIn("matrix_socolor_resistant_gray_20vol", names)
        self.assertGreaterEqual(len(records), 13)

    def test_idempotent_row_build_produces_same_ids(self) -> None:
        first = build_stage13_import_rows()
        second = build_stage13_import_rows()
        self.assertEqual(
            {r.package_rule_id: r.rule_id for r in first},
            {r.package_rule_id: r.rule_id for r in second},
        )

    def test_validation_case_and_workflow_counts(self) -> None:
        self.assertEqual(len(load_validation_cases()), 21)
        self.assertEqual(len(load_service_workflows()), 9)

    def test_inactive_dormant_rules_excluded_from_engine_records(self) -> None:
        rows = build_stage13_import_rows()
        dormant = [r for r in rows if r.is_dormant]
        if dormant:
            active_records = import_rows_to_formulation_rule_records(rows)
            dormant_names = {r.rule_name for r in dormant}
            active_names = {r.rule_name for r in active_records}
            self.assertFalse(dormant_names & active_names)


if __name__ == "__main__":
    unittest.main()
