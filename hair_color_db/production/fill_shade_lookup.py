"""Inventory-backed fill/repigmentation shade lookup for PostgreSQL."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, cast, select
from sqlalchemy.orm import Session

from src.fill_shade_lookup import (
    _is_natural_shade_code,
    _normalized_tones_for_families,
    _score_shade,
)

from .production_models import (
    Brand,
    NormalizedTone,
    ProductLine,
    ProductLineRegion,
    Shade,
    ShadeToneCode,
    ToneNormalization,
)
from .shade_matching import _load_normalized_tones_for_shades

_NATURAL_TONE_HINTS = frozenset({"Natural", "Neutral"})


def _candidate_rows(session: Session, *, canonical_key: str, level: int) -> list[Any]:
    return session.execute(
        select(
            Shade.shade_id,
            Shade.shade_code,
            Shade.shade_name,
            Shade.level,
            Shade.gray_coverage_claim,
            ProductLineRegion.canonical_key,
            ProductLine.product_line_name,
            Brand.brand_name,
        )
        .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
        .join(ProductLine, ProductLine.line_id == ProductLineRegion.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .where(ProductLineRegion.canonical_key == canonical_key)
        .where(Shade.level.is_not(None))
        .where(cast(Shade.level, Integer) == level)
        .where(Shade.is_active.is_(True))
        .order_by(Shade.shade_code)
    ).all()


def lookup_fill_shades_for_level(
    session: Session,
    *,
    canonical_key: str,
    level: int,
    tone_families: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return ranked PostgreSQL inventory shades for one fill step at a given level."""
    target_tones = _normalized_tones_for_families(tone_families)
    rows = _candidate_rows(session, canonical_key=canonical_key, level=level)
    tones_by_shade = _load_normalized_tones_for_shades(session, [row.shade_id for row in rows])

    ranked: list[dict[str, Any]] = []
    for row in rows:
        matched = tones_by_shade.get(row.shade_id, set())
        score = _score_shade(
            matched_tones=matched,
            target_tones=target_tones,
            gray_coverage_claim=row.gray_coverage_claim,
        )
        if score <= 0:
            continue
        ranked.append(
            {
                "shade_code": row.shade_code,
                "shade_name": row.shade_name,
                "shade_ref": f"{row.brand_name}::{row.product_line_name}::{row.shade_code}",
                "canonical_key": row.canonical_key,
                "level": float(row.level) if row.level is not None else None,
                "matched_tones": sorted(matched & target_tones),
                "match_score": round(score, 2),
            }
        )

    ranked.sort(key=lambda item: (-item["match_score"], item["shade_code"]))
    return ranked[:limit]


def lookup_natural_shades_at_level(
    session: Session,
    *,
    canonical_key: str,
    level: int,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return natural/neutral PostgreSQL inventory shades at the target level."""
    rows = _candidate_rows(session, canonical_key=canonical_key, level=level)
    tones_by_shade = _load_normalized_tones_for_shades(session, [row.shade_id for row in rows])

    ranked: list[dict[str, Any]] = []
    for row in rows:
        code = str(row.shade_code)
        matched = tones_by_shade.get(row.shade_id, set())
        natural_by_tone = bool(matched & _NATURAL_TONE_HINTS)
        natural_by_code = _is_natural_shade_code(code)
        if not natural_by_tone and not natural_by_code:
            continue
        score = 30.0 if natural_by_code and natural_by_tone else 20.0 if natural_by_code else 15.0
        ranked.append(
            {
                "shade_code": code,
                "shade_name": row.shade_name,
                "shade_ref": f"{row.brand_name}::{row.product_line_name}::{code}",
                "canonical_key": row.canonical_key,
                "level": float(row.level) if row.level is not None else None,
                "matched_tones": sorted(matched),
                "match_score": score,
                "role": "natural_base",
            }
        )

    ranked.sort(key=lambda item: (-item["match_score"], item["shade_code"]))
    return ranked[:limit]


def enrich_fill_guidance_with_inventory(
    session: Session,
    canonical_key: str | None,
    fill_guidance: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Attach PostgreSQL inventory shade suggestions to computed fill guidance."""
    if not fill_guidance or not canonical_key:
        return fill_guidance

    enriched = dict(fill_guidance)
    steps: list[dict[str, Any]] = []
    for step in fill_guidance.get("fill_steps", []):
        step_copy = dict(step)
        step_copy["suggested_shades"] = lookup_fill_shades_for_level(
            session,
            canonical_key=canonical_key,
            level=int(step["level"]),
            tone_families=list(step.get("suggested_tone_families", [])),
        )
        steps.append(step_copy)

    enriched["fill_steps"] = steps
    target_level = int(fill_guidance.get("target_level", 0) or 0)
    if target_level:
        enriched["target_natural_shades"] = lookup_natural_shades_at_level(
            session,
            canonical_key=canonical_key,
            level=target_level,
        )
    return enriched
