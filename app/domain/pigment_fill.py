"""Repigmentation / fill guidance when darkening multiple levels."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.paths import FORMULATION_ONTOLOGY_JSON

_ONTOLOGY_PATH = FORMULATION_ONTOLOGY_JSON

_TONE_FAMILIES: dict[str, list[str]] = {
    "Blue-violet": ["blue-violet", "ash-violet", "cool"],
    "Red-violet": ["violet-red", "burgundy", "cool-warm"],
    "Red-orange": ["orange-red", "copper-red", "warm"],
    "Orange": ["orange", "copper", "warm"],
    "Orange-yellow": ["gold", "orange-gold", "warm"],
    "Yellow-orange": ["gold", "yellow-gold", "warm"],
    "Yellow": ["yellow", "gold", "warm"],
    "Pale yellow": ["yellow", "gold", "pale-warm"],
}


@lru_cache(maxsize=1)
def _underlying_pigment_by_level() -> dict[int, dict[str, str]]:
    data = json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))
    mapping: dict[int, dict[str, str]] = {}
    for entry in data.get("underlying_pigment_default_map", []):
        level = int(entry["level"])
        mapping[level] = {
            "underlying_pigment": str(entry["underlying_pigment"]),
            "exposure_stage": str(entry.get("exposure_stage", "")),
        }
    return mapping


def compute_fill_guidance(
    *,
    starting_level: int,
    target_level: int,
) -> dict[str, Any]:
    """Build fill/repigmentation guidance for multi-level darkening."""
    if starting_level <= target_level:
        return {}

    pigment_map = _underlying_pigment_by_level()
    deposit_levels = starting_level - target_level
    fill_steps: list[dict[str, Any]] = []

    for level in range(starting_level - 1, target_level, -1):
        pigment_info = pigment_map.get(level, {})
        pigment = pigment_info.get("underlying_pigment", "Warm neutral")
        fill_steps.append(
            {
                "level": level,
                "underlying_pigment": pigment,
                "suggested_tone_families": _TONE_FAMILIES.get(
                    pigment, ["warm neutral", "gold", "copper"]
                ),
            }
        )

    target_pigment = pigment_map.get(target_level, {}).get("underlying_pigment")
    suggested_ratio = 0.25 if deposit_levels <= 2 else 0.35 if deposit_levels <= 3 else 0.45

    return {
        "starting_level": starting_level,
        "target_level": target_level,
        "deposit_levels": deposit_levels,
        "fill_steps": fill_steps,
        "target_underlying_pigment": target_pigment,
        "suggested_fill_ratio": suggested_ratio,
        "guidance": (
            "Multi-level darkening requires a fill or repigmentation formula before the "
            "final target base + tone. Blend warm fill tones (yellow → orange → red-orange) "
            "with the target shade or apply as a separate pre-step."
        ),
    }
