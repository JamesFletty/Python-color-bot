"""Tests for the FastAPI formula engine wrapper."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from api.main import app
from src.paths import DEFAULT_DB_PATH


@unittest.skipUnless(DEFAULT_DB_PATH.exists(), "SQLite database not initialized")
class FormulaApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["FORMULA_DB_PATH"] = str(DEFAULT_DB_PATH)
        cls.client = TestClient(app)

    def test_health_reports_database_ready(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["database_ready"])
        self.assertEqual(payload["status"], "ok")

    def test_formula_endpoint_returns_matrix_socolor(self) -> None:
        response = self.client.post(
            "/formula",
            json={
                "shade": "Matrix::SoColor::5N",
                "gray": 60,
                "service_intent": "gray_coverage",
                "porosity": 5,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "caution")
        self.assertIn("30", payload["formula"]["developer"])
        self.assertEqual(payload["formulation_rules"]["developer_volume"], 30)

    def test_formula_endpoint_404_for_unknown_shade(self) -> None:
        response = self.client.post(
            "/formula",
            json={"shade": "Matrix::SoColor::DOESNOTEXIST"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
