"""Derive normalized_tones on shade records from tone normalization maps."""

from __future__ import annotations

import re
from typing import Any

_LOREAL_PREFIX = "L'Oréal Professionnel::"

# Aveda booster / pure-tone shade_code → manufacturer_tone_code
AVEDA_SHADE_CODE_TO_TONE: dict[str, str] = {
    "Dark Y/O": "Y/O",
    "Light Y/O": "Y/O",
    "Pastel Y/O": "Y/O",
    "Dark R/O": "R/O",
    "Light O/R": "O/R",
    "Dark B/G": "B/G",
    "Dark B/V": "B/V",
    "Dark V/R": "V/R",
    "Light B/B": "B/B",
    "Light V/B": "V/B",
    "Pastel Blue": "Blue",
    "Pastel Violet": "Violet",
    "Natural Series": "Natural",
    "Intense Base": "Natural",
    "Universal ØN": "N/N",
    "ELC + Pastel Blue": "Blue",
    "ELC + Pastel Violet": "Violet",
    "ELC + Pastel Y/O": "Y/O",
    "Pastel Blue": "Blue",
    "Pastel Violet": "Violet",
}

# Category / non-color rows — not translatable shade codes.
NON_TRANSLATABLE_SHADE_CODES = frozenset(
    {
        "Pure Tones",
        "Pure Pigments",
        "Extra Lifting Creme",
    }
)


def normalize_loreal_tone_code(code: str) -> str:
    """Normalize L'Oréal dual-format tone codes (e.g. 31/7gB → 31, 3/6g → 3)."""
    cleaned = code.strip()
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]
    return cleaned


def infer_loreal_tone_suffix_from_shade(shade_code: str) -> str | None:
    """Extract digit suffix from L'Oréal shade notation (6.03 → 03, 7/7n → 0)."""
    code = shade_code.strip()
    if not code or code.lower() == "clear":
        return None
    dotted = re.match(r"^\d+\.(\d+)(?:/.*)?$", code)
    if dotted:
        return dotted.group(1)
    slash_natural = re.match(r"^\d+/(\w+)$", code, re.IGNORECASE)
    if slash_natural and slash_natural.group(1).lower().endswith("n"):
        return "0"
    if re.fullmatch(r"\d+", code):
        return "0"
    return None


def build_tone_map_index(
    mappings: list[dict[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    """canonical_key -> manufacturer_tone_code -> normalized_tones."""
    index: dict[str, dict[str, list[str]]] = {}
    for mapping in mappings:
        ck = mapping["canonical_key"]
        code = mapping["manufacturer_tone_code"]
        tones = list(mapping.get("normalized_tones") or [])
        index.setdefault(ck, {})[code] = tones
    return index


def infer_manufacturer_tone_codes(record: dict[str, Any]) -> list[str]:
    """Infer tone codes for a shade record when missing or placeholder."""
    existing = list(record.get("manufacturer_tone_codes") or [])
    shade_code = str(record.get("shade_code") or "").strip()
    canonical_key = record.get("canonical_key", "")

    if "Aveda::Full Spectrum" in canonical_key:
        if shade_code in AVEDA_SHADE_CODE_TO_TONE:
            return [AVEDA_SHADE_CODE_TO_TONE[shade_code]]
        normalized_existing: list[str] = []
        for code in existing:
            if code.startswith("Pastel "):
                normalized_existing.append(code.replace("Pastel ", ""))
            else:
                normalized_existing.append(code)
        if normalized_existing and normalized_existing != existing:
            return normalized_existing
        if existing:
            return existing
        m = re.fullmatch(r"(\d+)\s+R(?:\s+Intense)?", shade_code, re.IGNORECASE)
        if m:
            return ["R"]
        m = re.fullmatch(r"(\d+)\s+(\S+)(?:\s+Intense)?", shade_code)
        if m and m.group(2) not in {"Natural"}:
            return [m.group(2)]

    if canonical_key.startswith(_LOREAL_PREFIX):
        normalized = [normalize_loreal_tone_code(code) for code in existing if code]
        if normalized:
            return normalized
        suffix = infer_loreal_tone_suffix_from_shade(shade_code)
        if suffix is not None:
            return [suffix]

    return existing


def materialize_normalized_tones(
    record: dict[str, Any],
    tone_index: dict[str, dict[str, list[str]]],
) -> list[str]:
    """Return normalized tones for a shade record using tone map + inference."""
    canonical_key = record.get("canonical_key", "")
    shade_code = str(record.get("shade_code") or "").strip()
    if shade_code in NON_TRANSLATABLE_SHADE_CODES:
        return ["Other"]

    line_tones = tone_index.get(canonical_key, {})
    tone_codes = infer_manufacturer_tone_codes(record)
    collected: list[str] = []

    lookup_codes = list(tone_codes)
    if canonical_key.startswith(_LOREAL_PREFIX):
        lookup_codes = [normalize_loreal_tone_code(code) for code in tone_codes]

    for code in lookup_codes:
        for tone in line_tones.get(code, []):
            if tone not in collected:
                collected.append(tone)

    if collected and collected != ["Other"]:
        return collected

    # Pure pigment rows (Blue, Red, Violet, etc.) often carry the tone name directly.
    direct = line_tones.get(shade_code, [])
    if direct and direct != ["Other"]:
        return list(direct)

    # Keep existing non-Other tones if already set.
    existing = [t for t in (record.get("normalized_tones") or []) if t != "Other"]
    if existing:
        return existing

    return collected or list(record.get("normalized_tones") or ["Other"])
