"""Inventory-backed fill/repigmentation shade lookup (v2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import cast, Integer, select
from sqlalchemy.orm import Session

from src.fill_shade_lookup import (
    _is_natural_shade_code,
    _normalized_tones_for_families,
    _score_shade,
)

from app.models import Brand, ProductLine, Shade


def lookup_fill_shades_for_level(
    session: Session,
    *,
    canonical_key: str,
    level: int,
    tone_families: list[str],
    limit: int = 3,
) -> list[dict[str, Any]]:
    target_tones = _normalized_tones_for_families(tone_families)
    rows = session.execute(
        select(Shade, ProductLine, Brand)
        .join(ProductLine, ProductLine.line_id == Shade.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .where(ProductLine.canonical_key == canonical_key)
        .where(Shade.level.is_not(None))
        .where(cast(Shade.level, Integer) == level)
        .where(Shade.discontinued.is_(False))
        .order_by(Shade.shade_code)
    ).all()

    ranked: list[dict[str, Any]] = []
    for shade, line, brand in rows:
        matched = {tone.tone_name for tone in shade.tones}
        score = _score_shade(
            matched_tones=matched,
            target_tones=target_tones,
            gray_coverage_claim=shade.gray_coverage_claim,
        )
        if score <= 0:
            continue
        ranked.append(
            {
                "shade_code": shade.shade_code,
                "shade_name": shade.shade_name,
                "shade_ref": f"{brand.brand_name}::{line.line_name}::{shade.shade_code}",
                "canonical_key": line.canonical_key,
                "level": float(shade.level) if shade.level is not None else None,
                "matched_tones": sorted(matched & target_tones),
                "match_score": round(score, 2),
            }
        )

    ranked.sort(key=lambda item: (-item["match_score"], item["shade_code"]))
    return ranked[:limit]


def enrich_fill_guidance(
    session: Session,
    canonical_key: str | None,
    fill_guidance: dict[str, Any] | None,
) -> dict[str, Any] | None:
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
    return enriched
