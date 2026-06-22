"""v2 API integration tests."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from app.main import create_app


def _pg_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


@unittest.skipUnless(_pg_configured(), "DATABASE_URL not set")
class V2APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def test_health(self) -> None:
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("shade_count", body)
        self.assertIn("llm_configured", body)

    def test_list_brands(self) -> None:
        resp = self.client.get("/brands")
        self.assertEqual(resp.status_code, 200)
        brands = resp.json()
        self.assertGreater(len(brands), 0)
        self.assertIn("lines", brands[0])

    def test_list_line_shades(self) -> None:
        brands = self.client.get("/brands").json()
        line_id = None
        for brand in brands:
            for line in brand["lines"]:
                resp = self.client.get(f"/lines/{line['line_id']}/shades", params={"limit": 1})
                if resp.status_code == 200 and resp.json():
                    line_id = line["line_id"]
                    break
            if line_id is not None:
                break
        self.assertIsNotNone(line_id, "expected at least one line with shades")
        resp = self.client.get(f"/lines/{line_id}/shades", params={"limit": 10})
        self.assertEqual(resp.status_code, 200)
        shades = resp.json()
        self.assertGreater(len(shades), 0)
        self.assertIn("shade_code", shades[0])

    def test_post_formula(self) -> None:
        resp = self.client.post(
            "/formula",
            json={
                "shade": "Matrix::SoColor::5N",
                "gray_percent": 60,
                "service_intent": "gray_coverage",
                "current_level": 5,
                "desired_level": 5,
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn(body["status"], {"ok", "caution", "blocked"})
        self.assertIn("vol", body["formula"]["developer"])

    def test_ai_parse_deterministic(self) -> None:
        brands = self.client.get("/brands").json()
        line = brands[0]["lines"][0]
        resp = self.client.post(
            "/ai/parse",
            json={
                "user_input": "40g 07g 20g 09n gray coverage level 7",
                "color_line": line["line_name"],
                "line_id": line["line_id"],
                "canonical_key": line["canonical_key"],
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn(body["parse_source"], {"llm", "deterministic"})
        self.assertTrue(body["shade"])

    def test_ai_explain_without_llm_returns_503(self) -> None:
        if os.environ.get("LLM_API_KEY"):
            self.skipTest("LLM configured — 503 test not applicable")
        resp = self.client.post(
            "/ai/explain",
            json={
                "formula_result": {"status": "ok", "formula": {"developer": "20 vol"}},
                "user_input": "test",
                "color_line": "SoColor",
            },
        )
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    unittest.main()
