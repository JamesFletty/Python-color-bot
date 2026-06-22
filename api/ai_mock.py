"""Offline mock AI for local testing without external API keys.

Uses deterministic regex parsing plus the SQLite shade-matching engine to
produce structured requests and salon-style explanations.
"""

from __future__ import annotations

import re
from typing import Any

from src.matching import ShadeQuery

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
_SHADE_CODE_RE = re.compile(
    r"\b0?(\d{1,2})\s*(gi|gb|gv|v|g|n|a)\b",
    re.IGNORECASE,
)
_FORMULA_COMPONENT_RE = re.compile(
    r"(\d+)\s*g\s+(90v|0?\d{1,2}\s*(?:gi|gb|gv|v|g|n|a))\b",
    re.IGNORECASE,
)

_TONE_HINTS: dict[str, tuple[str, ...]] = {
    "strawberry blonde": ("Copper", "Red", "Gold"),
    "strawberry blond": ("Copper", "Red", "Gold"),
    "red violet": ("Red", "Violet"),
    "red-violet": ("Red", "Violet"),
    "violet red": ("Violet", "Red"),
    "violet-red": ("Violet", "Red"),
    "copper red": ("Copper", "Red"),
    "copper-red": ("Copper", "Red"),
    "gold iridescent": ("Gold", "Pearl"),
    "caramel": ("Gold", "Beige"),
    "butterscotch": ("Gold", "Beige"),
    "gold": ("Gold",),
    "gi": ("Gold", "Pearl"),
    "warm": ("Gold", "Warm"),
    "copper": ("Copper",),
    "ash": ("Ash",),
    "neutral": ("Natural",),
    "natural": ("Natural",),
    "violet": ("Violet",),
    "red": ("Red",),
    "mahogany": ("Mahogany",),
    "iridescent": ("Pearl",),
    "pearl": ("Pearl",),
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
    if "gold iridescent" in lowered or re.search(r"\bgi\b", lowered):
        return ("Gold", "Pearl")
    for keyword, tones in _TONE_HINTS.items():
        if keyword in lowered:
            return tones
    return ()


def _normalize_shade_token(level: int, suffix: str) -> str:
    return f"{level:02d}{suffix.upper()}"


def _shade_code_from_token(token: str) -> str | None:
    lowered = token.lower().replace(" ", "")
    if lowered == "90v":
        return "09V"
    match = _SHADE_CODE_RE.search(token)
    if not match:
        return None
    return _normalize_shade_token(int(match.group(1)), match.group(2))


def _infer_shade_codes(text: str) -> list[str]:
    """Extract likely Shades EQ shade codes from stylist formula shorthand."""
    components = _parse_formula_components(text)
    if components:
        codes: list[str] = []
        for _grams, token in components:
            code = _shade_code_from_token(token)
            if code and code not in codes:
                codes.append(code)
        return codes

    codes = []
    if re.search(r"\b90v\b", text, re.IGNORECASE):
        codes.append("09V")
    for match in _SHADE_CODE_RE.finditer(text):
        code = _normalize_shade_token(int(match.group(1)), match.group(2))
        if code not in codes:
            codes.append(code)
    return codes


def _parse_formula_components(text: str) -> list[tuple[int, str]]:
    """Return (grams, shade_token) pairs from stylist shorthand formulas."""
    components: list[tuple[int, str]] = []
    for match in _FORMULA_COMPONENT_RE.finditer(text):
        components.append((int(match.group(1)), match.group(2).strip()))
    return components


def _dia_light_equivalent(redken_code: str) -> tuple[str, str] | None:
    """Map Redken Shades EQ code to Dia Light shade + label."""
    level = _level_from_shade_code(redken_code)
    if level is None:
        return None
    suffix = redken_code[2:].upper()
    if suffix == "GI":
        return (f"{level}.03", "Honey Milkshake (Gold Iridescent)")
    if suffix == "V":
        return (f"{level}.1", "Icy Milkshake (violet)")
    if suffix == "G":
        return (f"{level}.3", "gold reflect")
    if suffix == "N":
        return (f"{level}", "natural")
    return None


def _level_from_shade_code(shade_code: str) -> int | None:
    prefix = re.match(r"^0*(\d{1,2})", shade_code)
    if not prefix:
        return None
    level = int(prefix.group(1))
    return level if 1 <= level <= 12 else None


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

    from api.backend import uses_postgres_engine
    from src.matching import ShadeQuery, fetch_shade_candidates

    requested = ShadeQuery(level=float(desired_level), tones=tones, gray_percent=float(gray))

    if uses_postgres_engine():
        from hair_color_db.production.db import create_session_factory, require_database_url
        from hair_color_db.production.shade_matching import fetch_shade_candidates as fetch_pg_candidates

        database_url = require_database_url()
        if not database_url:
            return None
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            matches = [
                match
                for match in fetch_pg_candidates(session, requested)
                if color_line.lower() in match["line"].lower()
            ]
    else:
        import sqlite3

        from src.paths import DEFAULT_DB_PATH

        conn = sqlite3.connect(DEFAULT_DB_PATH)
        try:
            matches = [
                match
                for match in fetch_shade_candidates(conn, requested)
                if color_line.lower() in match["line"].lower()
            ]
        finally:
            conn.close()

    if matches:
        return str(matches[0]["shade_code"])
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
    explicit_codes = _infer_shade_codes(user_input)
    if desired_level is None and explicit_codes:
        desired_level = _level_from_shade_code(explicit_codes[-1])
    if explicit_codes:
        shade = explicit_codes[-1]
    else:
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
    formula_block = formula_result.get("formula", {})
    hair = formula_result.get("hair_conditions", {})

    if not shade and formula_result.get("recommendation_status"):
        shade_code = "selected shade"
        shade_name = shade_code
        developer_label = (
            f"{formula_result['developer_volume']} vol"
            if formula_result.get("developer_volume") is not None
            else "line-appropriate developer"
        )
        mixing = "manufacturer mixing ratio"
        processing = "standard processing time"
        status = str(formula_result.get("recommendation_status", "ok"))
        fill = formula_result.get("fill_pigment_guidance")
    else:
        shade_code = shade.get("shade_code", "selected shade")
        shade_name = shade.get("shade_name") or shade_code
        developer_label = formula_block.get("developer") or "line-appropriate developer"
        mixing = formula_block.get("mixing_ratio") or "manufacturer mixing ratio"
        processing = formula_block.get("processing_time") or "standard processing time"
        status = str(formula_result.get("status", "ok"))
        fill = formula_block.get("fill_pigment_guidance")

    if mode == "translate":
        opener = (
            f"Translated into {color_line} using offline mock AI"
            f" ({translation_notes or 'tone/level mapping from source formula'})."
        )
    else:
        opener = (
            f"For the request described ({user_input.strip()[:120]}), "
            f"the engine selected {color_line} {shade_code} {shade_name}."
        )

    caution = ""
    if status == "caution":
        caution = " This service is flagged caution because depth or fill requirements apply."
    elif status == "blocked":
        caution = f" This recommendation is blocked: {formula_result.get('block_reason', 'rule conflict')}."

    fill_note = ""
    if fill:
        top_fill = ""
        steps = fill.get("fill_steps") or []
        if steps:
            suggestions = steps[0].get("suggested_shades") or []
            if suggestions:
                top = suggestions[0]
                top_fill = (
                    f" Pre-fill with {top['shade_code']} {top['shade_name']} "
                    f"at level {steps[0]['level']}, then "
                )
        fill_note = (
            f"{top_fill}apply the final formula at {mixing} with {developer_label} "
            f"for {processing}."
        )
    else:
        fill_note = f" Mix {mixing} with {developer_label} and process for {processing}."

    natural = hair.get("natural_level")
    desired = hair.get("desired_level")
    level_note = ""
    if natural is not None and desired is not None and natural != desired:
        direction = "darken" if desired < natural else "shift"
        level_note = (
            f" Starting level {natural:g} to target level {desired:g} "
            f"requires a {direction} service plan."
        )

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
    source_codes = _infer_shade_codes(source_formula)
    components = _parse_formula_components(source_formula)
    is_dia_light = target_line.lower().startswith("dia")

    if is_dia_light and components:
        translated_parts: list[str] = []
        dominant: tuple[int, str] | None = None
        for grams, token in components:
            source_code = _shade_code_from_token(token)
            if not source_code:
                continue
            equivalent = _dia_light_equivalent(source_code)
            if equivalent is None:
                continue
            target_shade, label = equivalent
            gi_note = " Gold Iridescent" if source_code.endswith("GI") else ""
            translated_parts.append(
                f"{grams}g Dia Light {target_shade} ({label}) from {source_code}{gi_note}"
            )
            if dominant is None or grams > dominant[0]:
                dominant = (grams, target_shade)
        if translated_parts:
            parsed["translation_notes"] = "; ".join(translated_parts)
            if dominant is not None:
                parsed["shade"] = dominant[1]
                parsed["desired_level"] = int(float(dominant[1].split(".")[0]))
    elif source_codes:
        gi_codes = [code for code in source_codes if code.endswith("GI")]
        v_codes = [code for code in source_codes if code.endswith("V")]
        if gi_codes and is_dia_light:
            parsed["shade"] = "9.03"
            parsed["desired_level"] = _level_from_shade_code(gi_codes[0]) or 9
            parsed["translation_notes"] = (
                f"Mapped Redken {gi_codes[0]} (Gold Iridescent) to Dia Light 9.03 Honey Milkshake; "
                f"gold/pearl reflect family."
            )
        elif gi_codes:
            parsed["shade"] = gi_codes[0]
        if v_codes and not parsed.get("translation_notes"):
            parsed["translation_notes"] = (
                f"Source includes {', '.join(v_codes)} violet tone; verify target-line violet equivalent."
            )

    source_label = source_line or "source line"
    if not parsed.get("translation_notes"):
        parsed["translation_notes"] = (
            f"Offline mock translation from {source_label} to {target_line} "
            f"matched level {parsed.get('desired_level')} and tone keywords in the source text."
        )
    parsed["line"] = target_line
    parsed.pop("_canonical_key", None)
    return parsed
