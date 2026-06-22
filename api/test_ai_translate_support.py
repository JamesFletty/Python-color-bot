"""Tests for database-grounded translation support."""

from __future__ import annotations

import unittest

from api.formula_text_parser import enrich_components_from_db, parse_formula_text, source_analysis_summary
from api.ai_translate_support import build_translation_context, ground_translation_result, resolve_shade_for_line


class FormulaTextParserTests(unittest.TestCase):
    def test_parses_aveda_copper_red_formula(self) -> None:
        text = "Aveda full spectrum 40g 6n 2g dark y/o 2g dark r/o 40g 20 vol"
        parsed = enrich_components_from_db(parse_formula_text(text))
        codes = [c.shade_code for c in parsed.components]
        self.assertIn("6 N/N", codes)
        self.assertIn("Dark Y/O", codes)
        self.assertIn("Dark R/O", codes)
        self.assertEqual(parsed.developer_volume, 20)
        summary = source_analysis_summary(parsed)
        self.assertIn("Dark Y/O", summary)
        self.assertIn("Dark R/O", summary)

    def test_parses_shades_eq_gold_and_cb(self) -> None:
        text = "redkin shades eq 20g 7g 20g 6cb 40g processing solution"
        parsed = enrich_components_from_db(parse_formula_text(text), line_hint="Shades EQ Gloss")
        codes = [c.shade_code for c in parsed.components]
        self.assertIn("07G", codes)
        self.assertIn("06CB", codes)

    def test_goal_text_infers_strawberry_blonde_tones(self) -> None:
        parsed = parse_formula_text(
            "My client is 50% grey and a natural level 6 and wants to be a level 8 strawberry blonde"
        )
        self.assertEqual(parsed.inferred_tones[:3], ("Copper", "Red", "Gold"))

    def test_goal_text_infers_intense_red_violet_tones(self) -> None:
        parsed = parse_formula_text("Level 3 natural 20% grey wants level 5 intense red violet")
        self.assertIn("Red", parsed.inferred_tones)
        self.assertIn("Violet", parsed.inferred_tones)


class TranslateGroundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from pathlib import Path
        from src.paths import DEFAULT_DB_PATH

        if not Path(DEFAULT_DB_PATH).exists():
            import init_db  # noqa: F401

    def test_majirel_6n_alias_resolves_to_catalog_code(self) -> None:
        from api.catalog import get_brands_and_lines

        majirel_id = None
        for brand in get_brands_and_lines():
            for line in brand["lines"]:
                if line["name"] == "Majirel":
                    majirel_id = line["id"]
        self.assertIsNotNone(majirel_id)
        resolved = resolve_shade_for_line("6N", line_id=majirel_id, product_line="Majirel")
        self.assertIsNotNone(resolved)
        self.assertIn(resolved["code"], {"6.0", "6"})

    def test_grounds_invalid_llm_shade_to_catalog_match(self) -> None:
        from api.catalog import get_brands_and_lines

        majirel_id = None
        for brand in get_brands_and_lines():
            for line in brand["lines"]:
                if line["name"] == "Majirel":
                    majirel_id = line["id"]
        self.assertIsNotNone(majirel_id)
        context = build_translation_context(
            "Aveda full spectrum 40g 6n 2g dark y/o 2g dark r/o 40g 20 vol",
            "Full Spectrum Permanent",
            target_line_id=majirel_id,
            target_line="Majirel",
        )
        grounded = ground_translation_result(
            {
                "shade": "6N",
                "desired_level": 6,
                "line": "Majirel",
                "translation_notes": "bad llm pick",
            },
            line_id=majirel_id,
            product_line="Majirel",
            context=context,
        )
        self.assertTrue(grounded.get("_grounded"))
        self.assertNotEqual(grounded["shade"], "6N")
        self.assertNotEqual(grounded["shade"], "6.0")
        resolved = resolve_shade_for_line(grounded["shade"], line_id=majirel_id, product_line="Majirel")
        self.assertIsNotNone(resolved)
        self.assertIn(grounded.get("grounding_note", ""), grounded.get("translation_notes", ""))

    def test_igora_9_66_not_in_catalog_gets_grounded(self) -> None:
        from api.catalog import get_brands_and_lines

        vibrance_id = None
        for brand in get_brands_and_lines():
            for line in brand["lines"]:
                if line["name"] == "IGORA VIBRANCE":
                    vibrance_id = line["id"]
        self.assertIsNotNone(vibrance_id)
        context = build_translation_context(
            "shades eq 20g 9p 20g 10v 40g processing solution",
            "Shades EQ Gloss",
            target_line_id=vibrance_id,
            target_line="IGORA VIBRANCE",
        )
        grounded = ground_translation_result(
            {"shade": "9-66", "desired_level": 9, "line": "IGORA VIBRANCE"},
            line_id=vibrance_id,
            product_line="IGORA VIBRANCE",
            context=context,
        )
        self.assertTrue(grounded.get("_grounded") or grounded.get("_grounding_failed") is None)
        resolved = resolve_shade_for_line(grounded["shade"], line_id=vibrance_id, product_line="IGORA VIBRANCE")
        self.assertIsNotNone(resolved)


if __name__ == "__main__":
    unittest.main()
