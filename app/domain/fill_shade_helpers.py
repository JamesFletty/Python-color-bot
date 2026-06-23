"""Tone-family mapping and scoring for fill/repigmentation shade lookup."""

from __future__ import annotations

_TONE_FAMILY_TO_NORMALIZED: dict[str, tuple[str, ...]] = {
    "gold": ("Gold",),
    "yellow": ("Gold", "Warm"),
    "yellow-gold": ("Gold", "Warm"),
    "yellow-orange": ("Gold", "Warm"),
    "orange-gold": ("Gold", "Copper"),
    "orange": ("Copper", "Warm", "Red"),
    "copper": ("Copper",),
    "copper-red": ("Copper", "Red"),
    "orange-red": ("Copper", "Red", "Warm"),
    "red-orange": ("Red", "Copper", "Warm"),
    "warm": ("Warm", "Gold", "Copper"),
    "warm neutral": ("Warm", "Neutral", "Natural"),
    "blue-violet": ("Violet", "Ash", "Cool"),
    "violet-red": ("Violet", "Red"),
    "burgundy": ("Red", "Mahogany"),
    "cool-warm": ("Warm", "Cool"),
    "pale-warm": ("Gold", "Warm"),
}


def normalized_tones_for_families(families: list[str]) -> set[str]:
    tones: set[str] = set()
    for family in families:
        key = family.lower().strip()
        for tone in _TONE_FAMILY_TO_NORMALIZED.get(key, ()):
            tones.add(tone)
        if not _TONE_FAMILY_TO_NORMALIZED.get(key):
            if "gold" in key:
                tones.add("Gold")
            if "copper" in key or "orange" in key:
                tones.update({"Copper", "Warm"})
            if "yellow" in key:
                tones.add("Gold")
            if "red" in key:
                tones.add("Red")
    return tones or {"Warm", "Gold", "Copper"}


def score_fill_shade(
    *,
    matched_tones: set[str],
    target_tones: set[str],
    gray_coverage_claim: str | None,
) -> float:
    if not target_tones:
        return 0.0
    overlap = matched_tones & target_tones
    if not overlap:
        return 0.0
    score = 20.0 * len(overlap)
    score += 10.0 * sum(1 for tone in overlap if tone in {"Gold", "Copper", "Warm", "Red"})
    if gray_coverage_claim:
        score += 5.0
    return score
