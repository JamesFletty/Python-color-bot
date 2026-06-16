"""Map fill/repigmentation guidance to concrete shades from the SQLite inventory."""

from __future__ import annotations

import sqlite3
from typing import Any

# Map fill tone-family labels to normalized tones stored in shade_normalized_tone.
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

_NATURAL_TONE_HINTS = frozenset({"Natural", "Neutral"})
_NATURAL_CODE_SUFFIXES = ("N", "NN", "NA", "NW", "NG", "/0", "/00")


def _normalized_tones_for_families(families: list[str]) -> set[str]:
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


def _is_natural_shade_code(shade_code: str) -> bool:
    code = shade_code.upper().replace(" ", "")
    if code.endswith("/0") or code.endswith("/00"):
        return True
    for suffix in _NATURAL_CODE_SUFFIXES:
        if code.endswith(suffix) and not code.endswith(f"{suffix}R"):
            return True
    return False


def _score_shade(
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


def lookup_fill_shades_for_level(
    conn: sqlite3.Connection,
    *,
    canonical_key: str,
    level: int,
    tone_families: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return ranked inventory shades for one fill step at a given level."""
    conn.row_factory = sqlite3.Row
    target_tones = _normalized_tones_for_families(tone_families)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            s.shade_code,
            s.shade_name,
            s.level,
            s.canonical_key,
            s.gray_coverage_claim,
            pl.product_line_name AS product_line,
            b.brand_name AS brand,
            GROUP_CONCAT(snt.tone_name, ',') AS tone_csv
        FROM shade s
        JOIN product_line pl ON pl.line_id = s.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        LEFT JOIN shade_normalized_tone snt ON snt.shade_id = s.shade_id
        WHERE s.canonical_key = ?
          AND s.level IS NOT NULL
          AND CAST(s.level AS INTEGER) = ?
        GROUP BY s.shade_id
        ORDER BY s.shade_code
        """,
        (canonical_key, level),
    )

    ranked: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        tone_csv = row["tone_csv"] or ""
        matched = {tone.strip() for tone in tone_csv.split(",") if tone.strip()}
        score = _score_shade(
            matched_tones=matched,
            target_tones=target_tones,
            gray_coverage_claim=row["gray_coverage_claim"],
        )
        if score <= 0:
            continue
        brand = str(row["brand"])
        line = str(row["product_line"])
        code = str(row["shade_code"])
        ranked.append(
            {
                "shade_code": code,
                "shade_name": row["shade_name"],
                "shade_ref": f"{brand}::{line}::{code}",
                "canonical_key": row["canonical_key"],
                "level": row["level"],
                "matched_tones": sorted(matched & target_tones),
                "match_score": round(score, 2),
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["match_score"],
            item["shade_code"],
        )
    )
    return ranked[:limit]


def lookup_natural_shades_at_level(
    conn: sqlite3.Connection,
    *,
    canonical_key: str,
    level: int,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return natural/neutral base shades at the target level for fill mixing."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            s.shade_code,
            s.shade_name,
            s.level,
            s.canonical_key,
            pl.product_line_name AS product_line,
            b.brand_name AS brand,
            GROUP_CONCAT(snt.tone_name, ',') AS tone_csv
        FROM shade s
        JOIN product_line pl ON pl.line_id = s.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        LEFT JOIN shade_normalized_tone snt ON snt.shade_id = s.shade_id
        WHERE s.canonical_key = ?
          AND s.level IS NOT NULL
          AND CAST(s.level AS INTEGER) = ?
        GROUP BY s.shade_id
        ORDER BY s.shade_code
        """,
        (canonical_key, level),
    )

    ranked: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        code = str(row["shade_code"])
        tone_csv = row["tone_csv"] or ""
        matched = {tone.strip() for tone in tone_csv.split(",") if tone.strip()}
        natural_by_tone = bool(matched & _NATURAL_TONE_HINTS)
        natural_by_code = _is_natural_shade_code(code)
        if not natural_by_tone and not natural_by_code:
            continue
        brand = str(row["brand"])
        line = str(row["product_line"])
        score = 30.0 if natural_by_code and natural_by_tone else 20.0 if natural_by_code else 15.0
        ranked.append(
            {
                "shade_code": code,
                "shade_name": row["shade_name"],
                "shade_ref": f"{brand}::{line}::{code}",
                "canonical_key": row["canonical_key"],
                "level": row["level"],
                "matched_tones": sorted(matched),
                "match_score": score,
                "role": "natural_base",
            }
        )

    ranked.sort(key=lambda item: (-item["match_score"], item["shade_code"]))
    return ranked[:limit]


def enrich_fill_guidance_with_inventory(
    conn: sqlite3.Connection,
    canonical_key: str,
    fill_guidance: dict[str, Any],
) -> dict[str, Any]:
    """Attach inventory shade suggestions to computed fill guidance."""
    if not fill_guidance:
        return fill_guidance

    enriched = dict(fill_guidance)
    steps: list[dict[str, Any]] = []
    for step in fill_guidance.get("fill_steps", []):
        level = int(step["level"])
        families = list(step.get("suggested_tone_families", []))
        step_copy = dict(step)
        step_copy["suggested_shades"] = lookup_fill_shades_for_level(
            conn,
            canonical_key=canonical_key,
            level=level,
            tone_families=families,
        )
        steps.append(step_copy)

    enriched["fill_steps"] = steps
    target_level = int(fill_guidance.get("target_level", 0))
    if target_level:
        enriched["target_natural_shades"] = lookup_natural_shades_at_level(
            conn,
            canonical_key=canonical_key,
            level=target_level,
        )
    return enriched
