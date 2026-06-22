"""Tests for reference pack import."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
