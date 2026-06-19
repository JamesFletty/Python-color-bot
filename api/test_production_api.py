"""Tests for PostgreSQL backend FastAPI routing."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from api.schemas import HealthResponse, ProductionFormulaResponse


class ProductionBackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_backend = os.environ.get("ENGINE_BACKEND")
        os.environ["ENGINE_BACKEND"] = "postgres"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self.original_backend is None:
            os.environ.pop("ENGINE_BACKEND", None)
        else:
            os.environ["ENGINE_BACKEND"] = self.original_backend

    def test_health_uses_postgres_readiness(self) -> None:
        readiness = HealthResponse(
            status="ok",
            backend="postgres",
            database_path="DATABASE_URL",
            database_ready=True,
            database_url_configured=True,
            pg_db_connected=True,
            stage12_shade_count=1828,
            stage12_ready=True,
            stage13_rule_count=42,
            stage13_ready=True,
        )
        with patch("api.main._production_health", return_value=readiness):
            response = self.client.get("/v1/production/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["backend"], "postgres")
        self.assertTrue(payload["database_ready"])
        self.assertTrue(payload["stage12_ready"])
        self.assertTrue(payload["stage13_ready"])

    def test_backend_switch_health_uses_postgres_readiness(self) -> None:
        readiness = HealthResponse(
            status="ok",
            backend="postgres",
            database_path="DATABASE_URL",
            database_ready=True,
            database_url_configured=True,
            pg_db_connected=True,
            stage12_shade_count=1828,
            stage12_ready=True,
            stage13_rule_count=42,
            stage13_ready=True,
        )
        with patch("api.main._pg_health", return_value=readiness):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["backend"], "postgres")
        self.assertTrue(payload["database_ready"])
        self.assertTrue(payload["stage12_ready"])
        self.assertTrue(payload["stage13_ready"])

    def test_formula_uses_production_backend(self) -> None:
        production_payload = ProductionFormulaResponse(
            recommendation_status="ok",
            matched_rules=[],
            matched_rule_names=["gray developer"],
            developer_volume=30,
            warnings=[],
            blocked_by=[],
            explanation_summary="Matched 1 formulation rule.",
            suggested_formula_steps=1,
            triggered_workflows=[],
            formula_zones=None,
            fill_pigment_guidance=None,
            quantity_rationale="60g target color based on medium hair.",
            audit_trail=[],
            formula_id=None,
            persisted=False,
        )
        with patch("api.main._production_formula", return_value=production_payload) as run_pg:
            response = self.client.post(
                "/v1/production/formula",
                json={
                    "shade": "Matrix::SoColor::5N",
                    "gray": 60,
                    "service_intent": "gray_coverage",
                    "porosity": 5,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {
                "recommendation_status",
                "matched_rules",
                "matched_rule_names",
                "developer_volume",
                "warnings",
                "blocked_by",
                "explanation_summary",
                "suggested_formula_steps",
                "triggered_workflows",
                "formula_zones",
                "fill_pigment_guidance",
                "quantity_rationale",
                "audit_trail",
                "formula_id",
                "persisted",
            },
        )
        self.assertEqual(payload["recommendation_status"], "ok")
        self.assertEqual(payload["developer_volume"], 30)
        self.assertEqual(payload["quantity_rationale"], "60g target color based on medium hair.")
        self.assertFalse(payload["persisted"])
        run_pg.assert_called_once()

    def test_backend_switch_formula_uses_production_backend(self) -> None:
        production_payload = ProductionFormulaResponse(
            recommendation_status="ok",
            matched_rules=[],
            matched_rule_names=[],
            developer_volume=20,
            warnings=[],
            blocked_by=[],
            explanation_summary="Matched 0 formulation rules.",
            suggested_formula_steps=1,
            persisted=False,
        )
        with patch("api.main._production_formula", return_value=production_payload) as run_pg:
            response = self.client.post(
                "/formula",
                json={
                    "shade": "Matrix::SoColor::5N",
                    "gray": 0,
                    "service_intent": "tone_deposit",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["developer_volume"], 20)
        run_pg.assert_called_once()


if __name__ == "__main__":
    unittest.main()
