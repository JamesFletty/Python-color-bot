"""xAI (Grok) integration for formula parsing and explanation."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import AsyncOpenAI


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url="https://api.x.ai/v1",
    )


_PARSE_SYSTEM = """\
You are an expert professional hair colorist and formula specialist.

Hair level scale: 1 (black) → 12 (lightest blonde).

service_intent values:
- "tone_deposit"   → depositing tone, same or darker level, no lift
- "lift_deposit"   → lifting 1–3 levels while depositing color
- "gray_coverage"  → client has gray/white hair that needs coverage
- "corrective"     → fixing a previous color mistake
- "fashion"        → vivid, non-natural fashion colors

Infer service_intent from context clues (gray percentage > 0 → likely gray_coverage, etc.).

Return ONLY valid compact JSON. No markdown fences, no explanation text."""

_TRANSLATE_SYSTEM = """\
You are an expert professional hair colorist specializing in cross-brand formula translation.

Tone mapping reference (approximate equivalents across systems):
- Natural/Neutral:   Wella /0  | Redken N   | Schwarzkopf -0  | Matrix N
- Ash/Cool:          Wella /1  | Redken A   | Schwarzkopf -1  | Matrix A
- Iridescent:        Wella /2  | Redken I   | Schwarzkopf -2
- Gold:              Wella /3  | Redken G   | Schwarzkopf -3  | Matrix G
- Red:               Wella /4  | Redken R   | Schwarzkopf -4  | Matrix R
- Mahogany:          Wella /5  | Redken RO  | Schwarzkopf -5  | Matrix M
- Violet:            Wella /6  | Redken V   | Schwarzkopf -6  | Matrix V
- Brown:             Wella /7  | Redken B   | Schwarzkopf -7  | Matrix B
- Pearl:             Wella /8  | Redken P   | Schwarzkopf -8
- Warm Brown:        Wella /7  | Redken NW  | Matrix W

Match level number exactly. Match tone family as closely as possible.

Return ONLY valid compact JSON. No markdown, no explanation outside the translation_notes field."""


async def parse_formula_request(
    user_input: str,
    color_line: str,
    canonical_key: str,
) -> dict[str, Any]:
    """Parse natural-language stylist input into structured engine parameters."""
    prompt = (
        f"The stylist is working with: {color_line}\n\n"
        f"Stylist input:\n{user_input}\n\n"
        f"Return JSON with ALL applicable fields:\n"
        f'{{"shade":"<code for {color_line}>","current_level":<1-12>,"gray":<0-100>,'
        f'"texture":"fine|medium|coarse","service_intent":"...","desired_level":<1-12>,'
        f'"porosity":<1-10 default 5>,"elasticity":<1-10 default 6>,"line":"{color_line}"}}'
    )
    resp = await _client().chat.completions.create(
        model="grok-3-mini",
        messages=[
            {"role": "system", "content": _PARSE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return json.loads(resp.choices[0].message.content)


async def explain_formula(
    formula_result: dict[str, Any],
    user_input: str,
    color_line: str,
    mode: str = "formula",
    translation_notes: str | None = None,
) -> str:
    """Generate a concise professional explanation of the formula."""
    if mode == "translate":
        context = (
            f"A stylist wants to translate this formula into {color_line}:\n{user_input}\n\n"
            f"Translation analysis: {translation_notes or 'see formula'}\n\n"
        )
    else:
        context = f"Stylist described: {user_input}\n\n"

    prompt = (
        f"{context}"
        f"Formula engine output:\n{json.dumps(formula_result, indent=2)}\n\n"
        "Write a 3–5 sentence professional explanation covering:\n"
        "1. Specific products selected and the clinical reason\n"
        "2. Developer strength and mix ratio rationale\n"
        "3. Expected result and any key application notes\n\n"
        "Be direct and specific. Professional salon language. No bullet points."
    )
    resp = await _client().chat.completions.create(
        model="grok-3-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior hair color educator explaining formulas to stylists. "
                    "Be concise, specific, and professional."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


async def translate_formula(
    source_formula: str,
    source_line: str | None,
    target_line: str,
    target_canonical_key: str,
) -> dict[str, Any]:
    """Translate a formula from one color line to another."""
    source_ctx = f"Source line: {source_line}" if source_line else "Source line: (infer from formula)"
    prompt = (
        f"Source formula:\n{source_formula}\n\n"
        f"{source_ctx}\n"
        f"Target line: {target_line} (canonical: {target_canonical_key})\n\n"
        f"Return JSON:\n"
        f'{{"shade":"<closest shade code in {target_line}>","current_level":<1-12>,'
        f'"gray":<0-100>,"texture":"fine|medium|coarse",'
        f'"service_intent":"tone_deposit|lift_deposit|gray_coverage|corrective|fashion",'
        f'"desired_level":<1-12>,"porosity":5,"elasticity":6,"line":"{target_line}",'
        f'"translation_notes":"<explain the tone/level mapping>"}}'
    )
    resp = await _client().chat.completions.create(
        model="grok-3",
        messages=[
            {"role": "system", "content": _TRANSLATE_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content)
