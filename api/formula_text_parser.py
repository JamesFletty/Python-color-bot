"""Deterministic parsing of stylist formula shorthand."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# e.g. 40g 6n, 20g 7g, 2g dark y/o, 40g 20 vol
_COMPONENT_RE = re.compile(
    r"(\d+)\s*g\s+"
    r"(dark\s*[yr]/o|light\s*[yr]/o|pastel\s*[yr]/o|"
    r"\d+\s*vol|"
    r"90v|"
    r"0?\d{1,2}\s*(?:gi|gb|gv|cb|rb|nw|na|gg|gn|vb|g|p|a|v)|"
    r"0?\d{1,2}\s*n/?n?|"
    r"0?\d{1,2}\s*[yr]/o)",
    re.IGNORECASE,
)
_SEQ_SUFFIXES = frozenset({"GI", "GB", "GV", "CB", "RB", "NW", "NA", "GG", "GN", "VB", "N", "G", "V", "A", "P"})


@dataclass
class FormulaComponent:
    grams: int
    token: str
    shade_code: str | None = None
    shade_name: str | None = None
    normalized_tones: tuple[str, ...] = ()
    level: float | None = None
    role: str = "color"  # color | developer | booster


@dataclass
class ParsedFormula:
    components: list[FormulaComponent] = field(default_factory=list)
    inferred_level: float | None = None
    inferred_tones: tuple[str, ...] = ()
    developer_volume: int | None = None
    source_line_hint: str | None = None


def _normalize_token(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip())


def _shade_code_from_token(token: str) -> str | None:
    cleaned = token.lower().replace(" ", "")
    if re.search(r"\d+vol", cleaned):
        return None
    if cleaned == "90v":
        return "09V"
    if cleaned == "darky/o":
        return "Dark Y/O"
    if cleaned == "darkr/o":
        return "Dark R/O"
    if cleaned == "lighty/o":
        return "Light Y/O"
    if cleaned == "lightr/o":
        return "Light R/O"

    m = re.fullmatch(r"0?(\d{1,2})n/?n?", cleaned)
    if m:
        return f"{int(m.group(1))} N/N"

    m = re.fullmatch(r"0?(\d{1,2})(gi|gb|gv|cb|rb|nw|na|gg|gn|vb|g|p|a)", cleaned)
    if m:
        level, suffix = int(m.group(1)), m.group(2).upper()
        return f"{level:02d}{suffix}"

    m = re.fullmatch(r"0?(\d{1,2})v", cleaned)
    if m:
        return f"{int(m.group(1)):02d}V"

    m = re.fullmatch(r"0?(\d{1,2})([yr])/o", cleaned)
    if m:
        return f"{int(m.group(1))} {'Y/O' if m.group(2).lower() == 'y' else 'R/O'}"

    # Aveda inventory shorthand: 6R/O, 6R (no spaces)
    m = re.fullmatch(r"0?(\d{1,2})r/o", cleaned)
    if m:
        return f"{int(m.group(1))} R/O"
    m = re.fullmatch(r"0?(\d{1,2})r", cleaned)
    if m:
        return f"{int(m.group(1))} R"

    return _normalize_token(token)


def parse_formula_text(text: str) -> ParsedFormula:
    """Extract gram-weighted components from free-text formula input."""
    result = ParsedFormula()
    lowered = text.lower()
    if "shades eq" in lowered or "shade eq" in lowered:
        result.source_line_hint = "Shades EQ Gloss"
    elif "full spectrum" in lowered or "aveda" in lowered:
        result.source_line_hint = "Full Spectrum Permanent"
    elif "majirel" in lowered:
        result.source_line_hint = "Majirel"
    elif "igora vibrance" in lowered or "vibrance" in lowered:
        result.source_line_hint = "IGORA VIBRANCE"

    for match in _COMPONENT_RE.finditer(text):
        grams = int(match.group(1))
        token = _normalize_token(match.group(2))
        if re.search(r"\d+\s*vol", token, re.IGNORECASE):
            vol = re.search(r"(\d+)", token)
            if vol:
                result.developer_volume = int(vol.group(1))
            continue
        code = _shade_code_from_token(token)
        result.components.append(
            FormulaComponent(grams=grams, token=token, shade_code=code)
        )

    levels = [c.level for c in result.components if c.level is not None]
    if levels:
        result.inferred_level = sum(levels) / len(levels)
    else:
        for comp in result.components:
            if comp.shade_code and re.match(r"^0?(\d{1,2})", comp.shade_code):
                result.inferred_level = float(re.match(r"^0?(\d{1,2})", comp.shade_code).group(1))  # type: ignore[union-attr]
                break

    tone_set: list[str] = []
    for comp in result.components:
        for tone in comp.normalized_tones:
            if tone not in tone_set:
                tone_set.append(tone)
    result.inferred_tones = tuple(tone_set)
    return result


def enrich_components_from_db(
    parsed: ParsedFormula,
    *,
    line_hint: str | None = None,
) -> ParsedFormula:
    """Attach catalog metadata to parsed components when shades exist in SQLite."""
    from api.ai_translate_support import lookup_shade_on_line

    effective_line = line_hint or parsed.source_line_hint
    tone_set: list[str] = list(parsed.inferred_tones)
    levels: list[float] = []

    for comp in parsed.components:
        token_lower = comp.token.lower()
        if "y/o" in token_lower:
            for tone in ("Gold", "Copper"):
                if tone not in tone_set:
                    tone_set.append(tone)
        if "r/o" in token_lower:
            for tone in ("Red", "Copper"):
                if tone not in tone_set:
                    tone_set.append(tone)
        if not comp.shade_code:
            continue
        row = lookup_shade_on_line(
            comp.shade_code,
            product_line_hint=effective_line,
        )
        if row is None:
            continue
        comp.shade_name = row.get("shade_name")
        comp.normalized_tones = tuple(row.get("normalized_tones") or ())
        if row.get("level") is not None:
            comp.level = float(row["level"])
            levels.append(comp.level)
        for tone in comp.normalized_tones:
            if tone not in tone_set and tone != "Other":
                tone_set.append(tone)

    if levels:
        parsed.inferred_level = sum(levels) / len(levels)
    parsed.inferred_tones = tuple(dict.fromkeys(tone_set))
    return parsed


def source_analysis_summary(parsed: ParsedFormula) -> str:
    """Human-readable summary of parsed source formula for LLM + notes."""
    if not parsed.components:
        return "No structured components parsed from source text."
    parts: list[str] = []
    for comp in parsed.components:
        label = comp.shade_code or comp.token
        if comp.shade_name:
            label = f"{label} ({comp.shade_name})"
        tone_note = ""
        if comp.normalized_tones:
            tone_note = f" tones={','.join(comp.normalized_tones)}"
        parts.append(f"{comp.grams}g {label}{tone_note}")
    summary = "; ".join(parts)
    if parsed.inferred_level is not None:
        summary += f" | blended level ~{parsed.inferred_level:g}"
    if parsed.inferred_tones:
        summary += f" | tone families: {', '.join(parsed.inferred_tones)}"
    if parsed.developer_volume:
        summary += f" | developer {parsed.developer_volume} vol"
    return summary
