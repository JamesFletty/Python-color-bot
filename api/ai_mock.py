"""Offline mock AI for local testing without external API keys.

Uses deterministic regex parsing plus the SQLite shade-matching engine to
produce structured requests and salon-style explanations.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from src.matching import ShadeQuery, fetch_shade_candidates
from src.paths import DEFAULT_DB_PATH

_LEVEL_RE = re.compile(
    r"(?:natural|current|starting|base|on)\s+(?:level|lvl|hair)?\s*(\d{1,2})|"
    r"(?:level|lvl)\s*(\d{1,2})\s+(?:hair|natural|base)",
    re.IGNORECASE,
)
_DESIRED_LEVEL_RE = re.compile(
    r"(?:looking for|want|target|desired|to)\s+(?:a\s+)?(?:level\s*)?(\d{1,2})|"
    r"(?:level|lvl)\s*(\d{1,2})\s+(?:caramel|tone|result|finish|color)",
    re.IGNORECASE,
)
_GRAY_RE = re.compile(r"(\d{1,3})\s*%\s*(?:gray|grey)", re.IGNORECASE)

_TONE_HINTS: dict[str, tuple[str, ...]] = {
    "caramel": ("Gold", "Beige"),
    "butterscotch": ("Gold", "Beige"),
    "gold": ("Gold",),
    "warm": ("Gold", "Warm"),
    "copper": ("Copper",),
    "ash": ("Ash",),
    "neutral": ("Natural",),
    "natural": ("Natural",),
    "violet": ("Violet",),
    "red": ("Red",),
    "mahogany": ("Mahogany",),
}


def _first_level(pattern: re.Pattern[str], text: str) -> int | None:
    for match in pattern.finditer(text):
        for group in match.groups():
            if group is not None:
                level = int(group)
                if 1 <= level <= 12:
                    return level
    return None


def _infer_tones(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    for keyword, tones in _TONE_HINTS.items():
        if keyword in lowered:
            return tones
    return ()


def _infer_service_intent(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(gray|grey)\b", lowered) and re.search(r"\bcover", lowered):
        return "gray_coverage"
    if any(word in lowered for word in ("correct", "fix", "brassy", "band")):
        return "corrective"
    if any(word in lowered for word in ("fashion", "vivid", "pastel", "pink", "blue")):
        return "fashion"
    if any(word in lowered for word in ("lift", "lighten", "lighter")):
        return "lift_deposit"
    return "tone_deposit"


def _pick_shade(
    *,
    color_line: str,
    desired_level: int | None,
    tones: tuple[str, ...],
    gray: int,
) -> str | None:
    if desired_level is None:
        return None
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    try:
        requested = ShadeQuery(level=float(desired_level), tones=tones, gray_percent=float(gray))
        matches = [
            match
            for match in fetch_shade_candidates(conn, requested)
            if color_line.lower() in match["line"].lower()
        ]
        if matches:
            return str(matches[0]["shade_code"])
    finally:
        conn.close()
    return None


def mock_parse_formula_request(
    user_input: str,
    color_line: str,
    canonical_key: str,
) -> dict[str, Any]:
    """Parse stylist text into engine parameters without calling an LLM."""
    current_level = _first_level(_LEVEL_RE, user_input)
    desired_level = _first_level(_DESIRED_LEVEL_RE, user_input)
    gray_match = _GRAY_RE.search(user_input)
    gray = int(gray_match.group(1)) if gray_match else 0
    tones = _infer_tones(user_input)
    shade = _pick_shade(
        color_line=color_line,
        desired_level=desired_level,
        tones=tones,
        gray=gray,
    )
    if shade is None and desired_level is not None:
        shade = f"{desired_level:02d}N"

    return {
        "shade": shade or "07N",
        "current_level": current_level,
        "gray": gray,
        "texture": "medium",
        "service_intent": _infer_service_intent(user_input),
        "desired_level": desired_level,
        "porosity": 5,
        "elasticity": 6,
        "line": color_line,
        "_mock": True,
        "_canonical_key": canonical_key,
    }


def mock_explain_formula(
    formula_result: dict[str, Any],
    user_input: str,
    color_line: str,
    mode: str = "formula",
    translation_notes: str | None = None,
) -> str:
    """Build a concise explanation from deterministic engine output."""
    shade = formula_result.get("shade", {})
    formula = formula_result.get("formula", {})
    hair = formula_result.get("hair_conditions", {})
    shade_code = shade.get("shade_code", "selected shade")
    shade_name = shade.get("shade_name") or shade_code
    developer = formula.get("developer") or "line-appropriate developer"
    mixing = formula.get("mixing_ratio") or "manufacturer mixing ratio"
    processing = formula.get("processing_time") or "standard processing time"
    status = formula_result.get("status", "ok")

    if mode == "translate":
        opener = (
            f"Translated into {color_line} using offline mock AI"
            f" ({translation_notes or 'tone/level mapping from source formula'})."
        )
    else:
        opener = f"For the request described ({user_input.strip()[:120]}), the engine selected {color_line} {shade_code} {shade_name}."

    caution = ""
    if status == "caution":
        caution = " This service is flagged caution because depth or fill requirements apply."
    elif status == "blocked":
        caution = f" This recommendation is blocked: {formula_result.get('block_reason', 'rule conflict')}."

    fill = formula.get("fill_pigment_guidance")
    fill_note = ""
    if fill:
        top_fill = ""
        steps = fill.get("fill_steps") or []
        if steps:
            suggestions = steps[0].get("suggested_shades") or []
            if suggestions:
                top = suggestions[0]
                top_fill = f" Pre-fill with {top['shade_code']} {top['shade_name']} at level {steps[0]['level']}, then "
        fill_note = (
            f"{top_fill}apply the final formula at {mixing} with {developer} for {processing}."
        )
    else:
        fill_note = f" Mix {mixing} with {developer} and process for {processing}."

    natural = hair.get("natural_level")
    desired = hair.get("desired_level")
    level_note = ""
    if natural is not None and desired is not None and natural != desired:
        direction = "darken" if desired < natural else "shift"
        level_note = f" Starting level {natural:g} to target level {desired:g} requires a {direction} service plan."

    return (
        "[Offline mock AI — no external API key required] "
        + opener
        + level_note
        + caution
        + fill_note
    )


def mock_translate_formula(
    source_formula: str,
    source_line: str | None,
    target_line: str,
    target_canonical_key: str,
) -> dict[str, Any]:
    """Translate a formula using the same offline heuristics as parse."""
    parsed = mock_parse_formula_request(source_formula, target_line, target_canonical_key)
    source_label = source_line or "source line"
    parsed["translation_notes"] = (
        f"Offline mock translation from {source_label} to {target_line} "
        f"matched level {parsed.get('desired_level')} and tone keywords in the source text."
    )
    parsed["line"] = target_line
    parsed.pop("_canonical_key", None)
    return parsed
