"""Tests for PostgreSQL shade search and reference lookup."""

from __future__ import annotations

import sqlite3
import unittest

from hair_color_db.production.pg_test_utils import get_postgres_test_context
from hair_color_db.production.production_models import ShadeToneCode
from hair_color_db.production.shade_matching import fetch_shade_candidates, lookup_shade_by_reference
from src.matching import ShadeQuery, fetch_shade_candidates as sqlite_fetch
from src.paths import DEFAULT_DB_PATH


class ShadeMatchingParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DEFAULT_DB_PATH.exists():
            raise unittest.SkipTest("SQLite database not initialized")

        context = get_postgres_test_context()
        cls.Session = context.Session
        cls.sqlite_conn = sqlite3.connect(DEFAULT_DB_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.sqlite_conn.close()

    def test_shade_tone_links_exist_after_import(self) -> None:
        with self.Session() as session:
            from sqlalchemy import func, select

            count = session.scalar(select(func.count()).select_from(ShadeToneCode))
        self.assertGreater(count or 0, 1000)

    def test_level_seven_ash_search_returns_matches(self) -> None:
        query = ShadeQuery(level=7.0, tones=("Ash",), brand="Wella")
        with self.Session() as session:
            pg_matches = fetch_shade_candidates(session, query)
        sqlite_matches = sqlite_fetch(self.sqlite_conn, query)

        self.assertGreater(len(pg_matches), 0)
        self.assertGreater(len(sqlite_matches), 0)
        self.assertIn("Ash", pg_matches[0]["normalized_tones"])

    def test_lookup_wella_koleston_permanent_7_1(self) -> None:
        with self.Session() as session:
            row = lookup_shade_by_reference(
                session,
                "Wella Professionals::Koleston Perfect::7/1",
            )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertIn("Koleston", row["product_line"])
        self.assertIn("permanent", (row.get("color_type") or "").lower())
        self.assertIn("Ash", row["normalized_tones"])

    def test_top_match_scores_align_with_sqlite_for_wella_ash(self) -> None:
        query = ShadeQuery(level=7.0, tones=("Ash",), brand="Wella")
        with self.Session() as session:
            pg_matches = fetch_shade_candidates(session, query)
        sqlite_matches = sqlite_fetch(self.sqlite_conn, query)

        pg_top = pg_matches[0]
        sqlite_top = sqlite_matches[0]
        self.assertEqual(pg_top["shade_code"], sqlite_top["shade_code"])
        self.assertEqual(pg_top["match_score"], sqlite_top["match_score"])


if __name__ == "__main__":
    unittest.main()
