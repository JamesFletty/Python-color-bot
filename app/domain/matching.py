"""Shade reference parsing and deterministic match scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ShadeQuery:
    """Normalized shade search parameters."""

    level: float
    tones: tuple[str, ...]
    gray_percent: float | None = None
    brand: str | None = None


def brand_matches(candidate: str, requested: str | None) -> bool:
    """Return True when requested brand filter matches candidate brand name."""
    if requested is None:
        return True
    candidate_lower = candidate.lower()
    requested_lower = requested.lower()
    return (
        requested_lower in candidate_lower
        or candidate_lower in requested_lower
        or requested_lower.replace(" ", "") in candidate_lower.replace(" ", "")
    )


def score_shade(
    *,
    requested: ShadeQuery,
    shade_level: float | None,
    shade_tones: set[str],
    shade_gray_claim: str | None,
    has_gray_rules: bool,
) -> tuple[float, dict[str, Any]]:
    """Compute a deterministic match score and score breakdown."""
    breakdown: dict[str, Any] = {
        "level_match": 0.0,
        "tone_matches": [],
        "tone_score": 0.0,
        "gray_bonus": 0.0,
    }
    if shade_level is None:
        return 0.0, breakdown

    level_delta = abs(shade_level - requested.level)
    if level_delta == 0:
        breakdown["level_match"] = 40.0
    elif level_delta <= 0.5:
        breakdown["level_match"] = 25.0
    elif level_delta <= 1.0:
        breakdown["level_match"] = 10.0
    else:
        return 0.0, breakdown

    if not requested.tones:
        breakdown["tone_score"] = 20.0
    else:
        per_tone = 60.0 / len(requested.tones)
        for tone in requested.tones:
            if tone in shade_tones:
                breakdown["tone_matches"].append(tone)
                breakdown["tone_score"] += per_tone

    if requested.gray_percent and requested.gray_percent > 0:
        if shade_gray_claim:
            breakdown["gray_bonus"] += 5.0
        if has_gray_rules:
            breakdown["gray_bonus"] += 5.0

    total = breakdown["level_match"] + breakdown["tone_score"] + breakdown["gray_bonus"]
    return round(total, 2), breakdown


def parse_shade_reference(shade_ref: str) -> tuple[str | None, str | None, str]:
    """
    Parse a shade reference like 'Wella 7/1' or 'Wella Professionals::Koleston Perfect::7/1'.

    Returns (brand_hint, product_line_hint, shade_code).
    """
    cleaned = shade_ref.strip()
    if "::" in cleaned:
        parts = [part.strip() for part in cleaned.split("::") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[-1]
        if len(parts) >= 2:
            return parts[0], None, parts[-1]

    tokens = cleaned.split()
    if len(tokens) == 2 and "/" in tokens[1]:
        return None, None, cleaned

    if len(tokens) >= 2:
        shade_code = tokens[-1]
        brand_hint = " ".join(tokens[:-1])
        return brand_hint, None, shade_code

    return None, None, cleaned
