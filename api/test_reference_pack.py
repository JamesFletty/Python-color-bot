"""Tests for reference pack import."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.tone_materialization import (
    infer_loreal_tone_suffix_from_shade,
    materialize_normalized_tones,
    normalize_loreal_tone_code,
    build_tone_map_index,
)


class ReferencePackTests(unittest.TestCase):
    def test_manifest_exists(self) -> None:
        manifest = Path("hair_color_db/reference/MANIFEST.json")
        self.assertTrue(manifest.exists())
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertIn("aveda", payload["directories"])

    def test_conversion_map_has_redken_melting_pairs(self) -> None:
        from src.paths import CROSS_LINE_JSON

        payload = json.loads(CROSS_LINE_JSON.read_text(encoding="utf-8"))
        ids = {e["conversion_id"] for e in payload["conversion_entries"]}
        self.assertTrue(any(i.startswith("gels_") and i.endswith("__seq") for i in ids))
        self.assertTrue(any(i.startswith("seq_") and i.endswith("__gels") for i in ids))

    def test_moroccanoil_tones_enriched(self) -> None:
        from src.paths import SHADES_JSON

        records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
        blue = next(
            r
            for r in records
            if r.get("canonical_key") == "Moroccanoil Professional::Color Rhapsody::US"
            and str(r.get("shade_code", "")).startswith("10.1")
        )
        self.assertIn("Blue", blue.get("normalized_tones", []))

    def test_tonal_reference_key_imported_for_majirel(self) -> None:
        from src.paths import TONE_MAP_JSON

        mappings = json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))["tone_normalization_map"]
        entry = next(
            e
            for e in mappings
            if e["canonical_key"] == "L'Oréal Professionnel::Majirel::US"
            and e["manufacturer_tone_code"] == "034"
        )
        self.assertIn("Gold", entry["normalized_tones"])
        self.assertIn("Copper", entry["normalized_tones"])

    def test_dia_richesse_has_digit_tone_map(self) -> None:
        from src.paths import TONE_MAP_JSON

        mappings = json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))["tone_normalization_map"]
        entry = next(
            e
            for e in mappings
            if e["canonical_key"] == "L'Oréal Professionnel::Dia Richesse::global"
            and e["manufacturer_tone_code"] == "32"
        )
        self.assertNotEqual(entry["normalized_tones"], ["Other"])

    def test_loreal_dual_code_normalization(self) -> None:
        self.assertEqual(normalize_loreal_tone_code("31/7gB"), "31")
        self.assertEqual(normalize_loreal_tone_code("3/6g"), "3")
        self.assertEqual(infer_loreal_tone_suffix_from_shade("6.03"), "03")
        self.assertEqual(infer_loreal_tone_suffix_from_shade("7/7n"), "0")

    def test_pravana_brand_conversions_imported(self) -> None:
        from src.paths import CROSS_LINE_JSON

        payload = json.loads(CROSS_LINE_JSON.read_text(encoding="utf-8"))
        ids = {e["conversion_id"] for e in payload["conversion_entries"]}
        self.assertIn("goldwell_6n__chromasilk", ids)
        self.assertIn("matrix_6n__chromasilk", ids)

    def test_pravana_naturals_added(self) -> None:
        from src.paths import SHADES_JSON

        records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
        six_n = next(
            r
            for r in records
            if r.get("canonical_key") == "Pravana::ChromaSilk Creme Color::US"
            and r.get("shade_code") == "6N"
        )
        self.assertIn("Natural", six_n.get("normalized_tones", []))

    def test_goldwell_to_pravana_conversion_resolves(self) -> None:
        from api.cross_line_conversion import lookup_conversion

        entry = lookup_conversion(
            source_canonical_key="Goldwell::Topchic::US",
            source_shade_code="6NA",
            target_canonical_key="Pravana::ChromaSilk Creme Color::US",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["strategy"], "fixed")
        self.assertIn(entry["target_shade_code"], {"6.22", "6N"})

    def test_matrix_color_insider_in_catalog(self) -> None:
        from src.paths import SHADES_JSON

        records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
        insider = [
            r for r in records if r.get("canonical_key") == "Matrix::Color Insider::US"
        ]
        self.assertGreaterEqual(len(insider), 58)
        six_n = next(r for r in insider if r.get("shade_code") == "6N")
        self.assertIn("Natural", six_n.get("normalized_tones", []))

    def test_seq_vibrance_chart_imported(self) -> None:
        from src.paths import CROSS_LINE_JSON

        payload = json.loads(CROSS_LINE_JSON.read_text(encoding="utf-8"))
        fixed = [
            e
            for e in payload["conversion_entries"]
            if e.get("conversion_id", "").endswith("__vibrance")
            and e.get("strategy") == "fixed"
        ]
        self.assertGreaterEqual(len(fixed), 60)
        ids = {e["conversion_id"] for e in fixed}
        self.assertIn("seq_09n__vibrance", ids)
        self.assertIn("seq_07g__vibrance", ids)

    def test_dia_light_dual_shade_materializes_tones(self) -> None:
        from src.paths import SHADES_JSON, TONE_MAP_JSON

        records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
        tone_index = build_tone_map_index(
            json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))["tone_normalization_map"]
        )
        record = next(
            r
            for r in records
            if r.get("shade_code") == "7.31/7gB"
            and "Dia Light" in r.get("canonical_key", "")
        )
        tones = materialize_normalized_tones(record, tone_index)
        self.assertIn("Gold", tones)
        self.assertNotEqual(tones, ["Other"])


if __name__ == "__main__":
    unittest.main()
