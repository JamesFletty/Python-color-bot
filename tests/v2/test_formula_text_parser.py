"""Formula text parser tests (ported for v2)."""

from __future__ import annotations

import unittest

from app.services.formula_text_parser import infer_goal_tones, parse_formula_text


class FormulaTextParserTests(unittest.TestCase):
    def test_parse_redken_shorthand(self) -> None:
        parsed = parse_formula_text("40g 07g 20g 09n 40g 20 vol")
        codes = [c.shade_code for c in parsed.components if c.shade_code]
        self.assertIn("07G", codes)
        self.assertIn("9 N/N", codes)
        self.assertEqual(parsed.developer_volume, 20)

    def test_infer_goal_tones(self) -> None:
        tones = infer_goal_tones("client wants strawberry blonde with gray coverage")
        self.assertIn("Copper", tones)
        self.assertIn("Natural", tones)

    def test_aveda_notation(self) -> None:
        parsed = parse_formula_text("30g 6R/O")
        self.assertEqual(len(parsed.components), 1)
        self.assertEqual(parsed.components[0].shade_code, "6 R/O")


if __name__ == "__main__":
    unittest.main()
