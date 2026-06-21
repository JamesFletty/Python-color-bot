"""Tests for offline mock AI parsing (no external API)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from api.ai_mock import (
    mock_explain_formula,
    mock_parse_formula_request,
    mock_translate_formula,
    _infer_shade_codes,
    _parse_formula_components,
)
from api.ai_service import get_ai_settings, resolve_ai_provider


class TestMockAI(unittest.TestCase):
    def test_defaults_to_mock_without_credentials(self) -> None:
        env = {
            "AI_PROVIDER": "",
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": "",
            "OPENAI_API_KEY": "",
            "XAI_API_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(resolve_ai_provider(), "mock")
            self.assertEqual(get_ai_settings().provider, "mock")

    def test_parses_redken_caramel_darkening_request(self) -> None:
        parsed = mock_parse_formula_request(
            user_input=(
                "Using Redken Shades EQ to deposit on level 9 hair "
                "and looking for a level 7 caramel tone"
            ),
            color_line="Shades EQ Gloss",
            canonical_key="Redken::Shades EQ Gloss::US",
        )
        self.assertEqual(parsed["current_level"], 9)
        self.assertEqual(parsed["desired_level"], 7)
        self.assertEqual(parsed["service_intent"], "tone_deposit")
        self.assertEqual(parsed["line"], "Shades EQ Gloss")
        self.assertIn(parsed["shade"], {"07GB", "07G", "07CB"})

    def test_explanation_mentions_offline_mode(self) -> None:
        formula = {
            "status": "caution",
            "shade": {"shade_code": "07GB", "shade_name": "Butterscotch"},
            "formula": {
                "developer": "5 vol",
                "mixing_ratio": "1:1",
                "processing_time": "20 minutes",
            },
            "hair_conditions": {"natural_level": 9, "desired_level": 7},
        }
        text = mock_explain_formula(
            formula,
            "level 9 to level 7 caramel",
            "Shades EQ Gloss",
        )
        self.assertIn("Offline mock AI", text)
        self.assertIn("07GB", text)

    def test_infers_gi_and_v_shorthand_codes(self) -> None:
        formula = "30g 90v 10g 9 gi 40g shades eq activator"
        self.assertEqual(_infer_shade_codes(formula), ["09V", "09GI"])
        self.assertEqual(
            _parse_formula_components(formula),
            [(30, "90v"), (10, "9 gi")],
        )

    def test_parses_gi_as_gold_iridescent_tones(self) -> None:
        parsed = mock_parse_formula_request(
            user_input="10g 9 gi on level 9",
            color_line="Shades EQ Gloss",
            canonical_key="Redken::Shades EQ Gloss::US",
        )
        self.assertEqual(parsed["shade"], "09GI")
        self.assertEqual(parsed["desired_level"], 9)

    def test_translates_shades_eq_formula_to_dia_light(self) -> None:
        source = "30g 90v 10g 9 gi 40g shades eq activator"
        parsed = mock_translate_formula(
            source_formula=source,
            source_line="Shades EQ Gloss",
            target_line="Dia Light",
            target_canonical_key="L'Oréal Professionnel::Dia Light::US",
        )
        self.assertEqual(parsed["shade"], "9.1")
        self.assertEqual(parsed["desired_level"], 9)
        notes = parsed["translation_notes"]
        self.assertIn("9.1", notes)
        self.assertIn("9.03", notes)
        self.assertIn("Gold Iridescent", notes)
        self.assertIn("09V", notes)
        self.assertIn("09GI", notes)


if __name__ == "__main__":
    unittest.main()
