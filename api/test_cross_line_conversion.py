"""Tests for cross-line conversion map and Aveda tone rematerialization."""

from __future__ import annotations

import unittest


class CrossLineConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path
        from src.paths import DEFAULT_DB_PATH

        if not Path(DEFAULT_DB_PATH).exists():
            import init_db  # noqa: F401

    def test_aveda_pure_tones_no_longer_other(self) -> None:
        from pathlib import Path
        import json
        from src.paths import SHADES_JSON

        records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
        boosters = {
            "Dark Y/O": ("Gold", "Copper"),
            "Dark R/O": ("Red", "Copper"),
            "Light Y/O": ("Gold", "Copper"),
            "6 R": ("Red",),
        }
        by_code = {
            r["shade_code"]: r
            for r in records
            if r.get("canonical_key") == "Aveda::Full Spectrum Permanent::US"
        }
        for code, expected in boosters.items():
            self.assertIn(code, by_code, msg=f"missing {code}")
            tones = tuple(by_code[code].get("normalized_tones") or [])
            for tone in expected:
                self.assertIn(tone, tones, msg=f"{code} missing {tone}")

    def test_aveda_formula_uses_cross_line_map_to_majirel(self) -> None:
        from api.ai_translate_support import build_translation_context
        from api.catalog import get_brands_and_lines

        majirel_id = None
        for brand in get_brands_and_lines():
            for line in brand["lines"]:
                if line["name"] == "Majirel":
                    majirel_id = line["id"]
        self.assertIsNotNone(majirel_id)
        ctx = build_translation_context(
            "Aveda full spectrum 40g 6n 2g dark y/o 2g dark r/o 40g 20 vol",
            "Full Spectrum Permanent",
            target_line_id=majirel_id,
            target_line="Majirel",
            source_canonical_key="Aveda::Full Spectrum Permanent::US",
            target_canonical_key="L'Oréal Professionnel::Majirel::US",
        )
        pick = ctx["deterministic_pick"]
        self.assertIsNotNone(pick)
        self.assertTrue(pick.get("_via_cross_line_map") or pick.get("conversion_notes"))
        self.assertNotIn(pick["code"], {"6.0", "6N"})

    def test_seq_09p_fixed_conversion_to_vibrance(self) -> None:
        from api.cross_line_conversion import lookup_conversion

        entry = lookup_conversion(
            source_canonical_key="Redken::Shades EQ Gloss::US",
            source_shade_code="09P",
            target_canonical_key="Schwarzkopf Professional::IGORA VIBRANCE::US",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["strategy"], "fixed")
        self.assertEqual(entry["target_shade_code"], "9-1")

    def test_seq_09p_fixed_conversion_to_vibrance(self) -> None:
        from api.cross_line_conversion import lookup_conversion

        entry = lookup_conversion(
            source_canonical_key="Redken::Shades EQ Gloss::US",
            source_shade_code="09P",
            target_canonical_key="Schwarzkopf Professional::IGORA VIBRANCE::US",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["strategy"], "fixed")
        self.assertEqual(entry["target_shade_code"], "9-1")
        self.assertEqual(entry["conversion_id"], "seq_09p__vibrance")

    def test_seq_09n_fixed_conversion_to_vibrance(self) -> None:
        from api.cross_line_conversion import lookup_conversion

        entry = lookup_conversion(
            source_canonical_key="Redken::Shades EQ Gloss::US",
            source_shade_code="09N",
            target_canonical_key="Schwarzkopf Professional::IGORA VIBRANCE::US",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["strategy"], "fixed")
        self.assertEqual(entry["target_shade_code"], "9-0")
        self.assertIn("9-0 + 9-1", entry.get("notes", ""))

    def test_matrix_insider_conversion_resolves(self) -> None:
        from api.cross_line_conversion import lookup_conversion
        from api.shade_catalog import lookup_shade_exact

        source = lookup_shade_exact("6N", product_line_hint="Color Insider")
        self.assertIsNotNone(source)
        entry = lookup_conversion(
            source_canonical_key="Matrix::Color Insider::US",
            source_shade_code="6N",
            target_canonical_key="Pravana::ChromaSilk Creme Color::US",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["target_shade_code"], "6N")

    def test_conversion_map_loaded_in_db(self) -> None:
        import sqlite3
        from src.paths import DEFAULT_DB_PATH

        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            count = conn.execute("SELECT COUNT(*) FROM cross_line_conversion").fetchone()[0]
        self.assertGreaterEqual(count, 600)


if __name__ == "__main__":
    unittest.main()
