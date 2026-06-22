"""Shade resolution and ranking for v2 PostgreSQL catalog."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.matching import ShadeQuery, brand_matches, parse_shade_reference, score_shade

from app.services.engine_models import ResolvedShade
from app.services.repository import EngineRepository


class ShadeNotFoundError(LookupError):
    def __init__(self, shade_ref: str) -> None:
        super().__init__(f"Shade not found: {shade_ref}")
        self.shade_ref = shade_ref


def _is_permanent_color_type(color_type: str | None) -> bool:
    if not color_type:
        return False
    return color_type.lower() in {"permanent", "perm"}


def resolve_shade(
    session: Session,
    shade_ref: str,
    *,
    line_hint: str | None = None,
) -> ResolvedShade:
    """Resolve a shade reference string to a catalog row."""
    repo = EngineRepository(session)
    brand_hint, line_hint_from_ref, shade_code = parse_shade_reference(shade_ref)
    effective_line_hint = line_hint or line_hint_from_ref

    candidates = repo.find_shades_by_code(
        shade_code,
        brand_hint=brand_hint,
        line_hint=effective_line_hint,
    )
    if not candidates:
        raise ShadeNotFoundError(shade_ref)

    if effective_line_hint:
        line_filtered = [
            shade
            for shade in candidates
            if effective_line_hint.lower() in (shade.line.line_name or "").lower()
            or effective_line_hint.lower() in (shade.line.canonical_key or "").lower()
        ]
        if line_filtered:
            candidates = line_filtered

    if brand_hint:
        brand_filtered = [
            shade
            for shade in candidates
            if brand_matches(shade.line.brand.brand_name, brand_hint)
        ]
        if brand_filtered:
            candidates = brand_filtered

    permanent = [shade for shade in candidates if _is_permanent_color_type(shade.color_type)]
    if permanent:
        candidates = permanent

    chosen = candidates[0]
    return ResolvedShade(**repo.shade_to_resolved(chosen))


def rank_shade_candidates(
    session: Session,
    *,
    level: float,
    tones: tuple[str, ...] = (),
    gray_percent: float | None = None,
    brand: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return ranked shade matches for catalog search."""
    repo = EngineRepository(session)
    requested = ShadeQuery(level=level, tones=tones, gray_percent=gray_percent, brand=brand)
    level_min = requested.level - 1.0
    level_max = requested.level + 1.0

    from sqlalchemy import select

    from app.models import Brand, ProductLine, Shade

    rows = session.execute(
        select(Shade, ProductLine, Brand)
        .join(ProductLine, ProductLine.line_id == Shade.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .where(Shade.level.is_not(None))
        .where(Shade.level >= level_min)
        .where(Shade.level <= level_max)
        .where(Shade.discontinued.is_(False))
    ).all()

    matches: list[dict[str, Any]] = []
    for shade, line, brand_row in rows:
        if not brand_matches(brand_row.brand_name, requested.brand):
            continue
        shade_tones = {tone.tone_name for tone in shade.tones}
        shade_level = float(shade.level) if shade.level is not None else None
        score, breakdown = score_shade(
            requested=requested,
            shade_level=shade_level,
            shade_tones=shade_tones,
            shade_gray_claim=shade.gray_coverage_claim,
            has_gray_rules=False,
        )
        if score <= 0:
            continue
        resolved = repo.shade_to_resolved(shade)
        resolved["match_score"] = score
        resolved["score_breakdown"] = breakdown
        matches.append(resolved)

    matches.sort(
        key=lambda item: (
            -item["match_score"],
            item["brand"],
            item["product_line"],
            item["shade_code"],
        )
    )
    return matches[:limit]
