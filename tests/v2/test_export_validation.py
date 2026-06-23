"""Validate v2 Phase 1 CSV exports against stage12/stage13 source counts."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.v2_paths import (
    BRANDS_LINES_CSV,
    CROSS_LINE_MAPPINGS_CSV,
    EXPECTED_CROSS_LINE_COUNT,
    EXPECTED_SHADE_COUNT,
    FORMULATION_RULES_CSV,
    SEED_DIR,
    SHADES_CSV,
)


def _count_csv_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class ExportValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SHADES_CSV.exists():
            raise unittest.SkipTest(
                "Seed CSVs missing — run scripts/export_*.py before tests"
            )

    def test_seed_directory_exists(self) -> None:
        self.assertTrue(SEED_DIR.is_dir())

    def test_shade_count(self) -> None:
        self.assertEqual(_count_csv_rows(SHADES_CSV), EXPECTED_SHADE_COUNT)

    def test_cross_line_count(self) -> None:
        self.assertEqual(_count_csv_rows(CROSS_LINE_MAPPINGS_CSV), EXPECTED_CROSS_LINE_COUNT)

    def test_formulation_rules_present(self) -> None:
        count = _count_csv_rows(FORMULATION_RULES_CSV)
        self.assertEqual(count, 143)

    def test_brands_lines_present(self) -> None:
        count = _count_csv_rows(BRANDS_LINES_CSV)
        self.assertGreaterEqual(count, 100)

    def test_line_technical_defaults_exported(self) -> None:
        rows = _csv_rows(BRANDS_LINES_CSV)
        matrix = next(row for row in rows if row["canonical_key"] == "Matrix::SoColor::US")
        self.assertEqual(matrix["mixing_ratio_default"], "1:1")
        self.assertEqual(matrix["developer_default_volume"], "20")
        self.assertTrue(matrix["processing_time_default_minutes"])
        self.assertIn("technical_defaults_json", matrix)


if __name__ == "__main__":
    unittest.main()
