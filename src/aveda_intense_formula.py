"""Aveda Full Spectrum Intense Series formula assembly (AV_FS_007)."""

from __future__ import annotations

import re
from typing import Any

_NATURAL_SHADE_G = 10
_INTENSE_BASE_G = 30

_MODIFIER_G_BY_LEVEL: dict[int, int] = {
    3: 16, 4: 12, 5: 8, 6: 4,
    7: 16, 8: 12, 9: 8, 10: 4,
}

_MODIFIER_BY_FAMILY: dict[str, dict[str, str]] = {
    "intense_violet_red": {
        "low": "Dark V/R",
    },
    "intense_red": {
        "low": "Red Pure Pigment",
    },
    "intense_copper": {
        "low": "Dark R/O",
        "high": "Light O/R",
    },
    "intense_ash": {
        "low": "Dark B/G",
        "high": "Light B/B",
    },
}

_DEVELOPER_BY_LIFT: list[tuple[int, int]] = [
    (4, 40), (3, 30), (2, 30), (1, 20), (0, 10),
]

_INTENSE_SUB_RANGES = {"Intense Series Customization"}


def is_aveda_full_spectrum(product_line: str, canonical_key: str | None = None) -> bool:
    if canonical_key and "Aveda::Full Spectrum Permanent" in canonical_key:
        return True
    return "full spectrum" in product_line.lower()


def is_intense_series_shade(shade_code: str, sub_range: str | None = None) -> bool:
    if sub_range in _INTENSE_SUB_RANGES:
        return True
    code = shade_code.upper()
    return bool(
        re.search(r"\bINTENSE\b", code)
        or re.search(r"V/R|R/V", code)
        or re.search(r"\b[3-9]\s+R\b$", code)
    )


def _tone_family(shade_code: str) -> str:
    code = shade_code.upper()
    if re.search(r"V/R|R/V", code):
        return "intense_violet_red"
    if re.search(r"R/O\s+INTENSE|O/R\s+INTENSE|R/O$|O/R$", code):
        return "intense_copper"
    if re.search(r"\bR\s+INTENSE\b|\bR$", code):
        return "intense_red"
    if re.search(r"B/G|B/B", code):
        return "intense_ash"
    return "intense_violet_red"


def _modifier_for(shade_code: str, desired_level: int) -> str | None:
    family = _tone_family(shade_code)
    mapping = _MODIFIER_BY_FAMILY.get(family, {})
    if desired_level <= 6:
        return mapping.get("low")
    return mapping.get("high") or mapping.get("low")


def _developer_vol(lift: float) -> int:
    for threshold, vol in _DEVELOPER_BY_LIFT:
        if lift >= threshold:
            return vol
    return 20


def build_intense_formula_components(
    shade_code: str,
    *,
    desired_level: int,
    current_level: int | None = None,
) -> dict[str, Any]:
    """Return multi-component Aveda intense formula from AV_FS_007.

    Components:
      - {desired_level} N/N  → natural base shade
      - Intense Base          → tone intensifier (ØN)
      - Dark/Light modifier   → tone booster for the target family

    Returns a dict with keys: components, developer, mixing_ratio.
    """
    natural_shade = f"{desired_level} N/N"
    modifier_g = _MODIFIER_G_BY_LEVEL.get(desired_level, 8)
    modifier = _modifier_for(shade_code, desired_level)

    lift = float(desired_level - current_level) if current_level is not None else 2.0
    developer_vol = _developer_vol(lift)

    components: list[dict[str, Any]] = [
        {"product": natural_shade, "grams": _NATURAL_SHADE_G, "role": "base"},
        {"product": "Intense Base", "grams": _INTENSE_BASE_G, "role": "intensifier"},
    ]
    if modifier:
        components.append({"product": modifier, "grams": modifier_g, "role": "booster"})

    return {
        "components": components,
        "developer": f"{developer_vol} vol",
        "developer_volume": developer_vol,
        "mixing_ratio": "1:1",
        "developer_ml": 40,
        "rule": "aveda_intense_series_customization_matrix (AV_FS_007)",
    }
