"""Formula engine integration tests against seeded PostgreSQL."""

from __future__ import annotations

import os
import unittest

from sqlalchemy import func, select

from app.db import get_session_factory
from app.models import Shade
from app.schemas.formula import FormulaRequest
from app.services.formula_engine import build_formula
from app.services.shade_matcher import resolve_shade


def _pg_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


@unittest.skipUnless(_pg_configured(), "DATABASE_URL not set")
class FormulaEngineIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        session = get_session_factory()()
        try:
            count = session.scalar(select(func.count()).select_from(Shade)) or 0
            if count == 0:
                raise unittest.SkipTest("v2 catalog not seeded — run scripts/bootstrap_v2.py")
        finally:
            session.close()

    def test_resolve_matrix_socolor_shade(self) -> None:
        session = get_session_factory()()
        try:
            shade = resolve_shade(session, "Matrix::SoColor::5N")
            self.assertIn("Matrix", shade.brand)
            self.assertEqual(shade.shade_code, "5N")
        finally:
            session.close()

    def test_build_formula_gray_coverage(self) -> None:
        session = get_session_factory()()
        try:
            response = build_formula(
                FormulaRequest(
                    shade="Matrix::SoColor::5N",
                    gray_percent=75,
                    service_intent="gray_coverage",
                    current_level=5,
                    desired_level=5,
                ),
                session,
            )
            self.assertIn(response.status, {"ok", "caution"})
            self.assertIn("vol", response.formula.developer)
            self.assertTrue(response.shade.shade_code)
        finally:
            session.close()

    def test_shade_count_matches_inventory(self) -> None:
        session = get_session_factory()()
        try:
            count = session.scalar(select(func.count()).select_from(Shade)) or 0
            self.assertGreaterEqual(count, 2530)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
