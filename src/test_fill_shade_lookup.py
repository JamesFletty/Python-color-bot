"""Tests for inventory-backed fill shade lookup."""

from __future__ import annotations

import sqlite3
import unittest

from src.fill_shade_lookup import enrich_fill_guidance_with_inventory, lookup_fill_shades_for_level
from src.paths import DEFAULT_DB_PATH
from hair_color_db.stage13_formulation_rules.pigment_fill import compute_fill_guidance


@unittest.skipUnless(DEFAULT_DB_PATH.exists(), "SQLite database not initialized")
class FillShadeLookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(DEFAULT_DB_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def test_warm_shades_at_level_eight_for_matrix(self) -> None:
        shades = lookup_fill_shades_for_level(
            self.conn,
            canonical_key="Matrix::SoColor::US",
            level=8,
            tone_families=["gold", "yellow-orange", "warm"],
        )
        self.assertTrue(shades)
        self.assertTrue(
            any(
                "Gold" in s["matched_tones"]
                or "Warm" in s["matched_tones"]
                or "Copper" in s["matched_tones"]
                for s in shades
            )
        )

    def test_enrich_adds_inventory_to_fill_guidance(self) -> None:
        guidance = compute_fill_guidance(starting_level=9, target_level=5)
        enriched = enrich_fill_guidance_with_inventory(
            self.conn,
            "Matrix::SoColor::US",
            guidance,
        )
        self.assertTrue(enriched["fill_steps"])
        self.assertTrue(enriched["fill_steps"][0].get("suggested_shades"))
        self.assertTrue(enriched.get("target_natural_shades"))


if __name__ == "__main__":
    unittest.main()
