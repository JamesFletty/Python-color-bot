"""PostgreSQL shade search, ranking, and reference lookup."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.matching import (
    ShadeQuery,
    _is_permanent_color_type,
    brand_matches,
    parse_shade_reference,
    score_shade,
)

from .production_models import (
    Brand,
    LineTechnicalRule,
    NormalizedTone,
    ProductLine,
    ProductLineRegion,
    Shade,
    ShadeRaw,
    ShadeToneCode,
    SourceDocument,
    SubRange,
    ToneCodeReference,
    ToneNormalization,
)


def _load_normalized_tones_for_shades(
    session: Session, shade_ids: list[uuid.UUID]
) -> dict[uuid.UUID, set[str]]:
    if not shade_ids:
        return {}

    rows = session.execute(
        select(ShadeToneCode.shade_id, NormalizedTone.tone_name)
        .join(
            ToneNormalization,
            ToneNormalization.tone_code_id == ShadeToneCode.tone_code_id,
        )
        .join(
            NormalizedTone,
            NormalizedTone.normalized_tone_id == ToneNormalization.normalized_tone_id,
        )
        .where(ShadeToneCode.shade_id.in_(shade_ids))
    ).all()

    tones_by_shade: dict[uuid.UUID, set[str]] = {}
    for shade_id, tone_name in rows:
        tones_by_shade.setdefault(shade_id, set()).add(str(tone_name))
    return tones_by_shade


def _load_gray_rule_regions(session: Session) -> set[uuid.UUID]:
    rows = session.scalars(
        select(distinct(LineTechnicalRule.line_region_id)).where(
            LineTechnicalRule.rule_type == "gray_coverage"
        )
    ).all()
    return set(rows)


def fetch_shade_candidates(
    session: Session,
    requested: ShadeQuery,
) -> list[dict[str, Any]]:
    """Query PostgreSQL for shade candidates and return ranked matches."""
    level_min = requested.level - 1.0
    level_max = requested.level + 1.0

    stmt = (
        select(
            Shade.shade_id,
            Shade.shade_code,
            Shade.shade_name,
            Shade.level,
            Shade.gray_coverage_claim,
            Shade.color_type,
            ProductLineRegion.canonical_key,
            ProductLineRegion.line_region_id,
            ProductLine.line_id,
            ProductLine.product_line_name,
            Brand.brand_name,
            SubRange.sub_range_name,
            SourceDocument.source_url,
            SourceDocument.source_title,
            ShadeRaw.source_confidence,
            ShadeRaw.evidence_status,
        )
        .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
        .join(ProductLine, ProductLine.line_id == ProductLineRegion.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .join(ShadeRaw, ShadeRaw.shade_raw_id == Shade.shade_raw_id)
        .outerjoin(SourceDocument, SourceDocument.source_id == ShadeRaw.source_id)
        .outerjoin(SubRange, SubRange.sub_range_id == Shade.sub_range_id)
        .where(Shade.level.is_not(None))
        .where(Shade.level.between(level_min, level_max))
        .where(Shade.is_active.is_(True))
    )
    rows = session.execute(stmt).all()
    if not rows:
        return []

    shade_ids = [row.shade_id for row in rows]
    tones_by_shade = _load_normalized_tones_for_shades(session, shade_ids)
    gray_rule_regions = _load_gray_rule_regions(session)

    matches: list[dict[str, Any]] = []
    for row in rows:
        brand = str(row.brand_name)
        if not brand_matches(brand, requested.brand):
            continue

        shade_tones = tones_by_shade.get(row.shade_id, set())
        shade_level = float(row.level) if row.level is not None else None
        score, breakdown = score_shade(
            requested=requested,
            shade_level=shade_level,
            shade_tones=shade_tones,
            shade_gray_claim=row.gray_coverage_claim,
            has_gray_rules=row.line_region_id in gray_rule_regions,
        )
        if score <= 0:
            continue

        provenance_links = []
        if row.source_url:
            provenance_links.append(
                {
                    "role": "primary",
                    "url": row.source_url,
                    "document": row.source_title,
                    "confidence": row.source_confidence,
                    "evidence_status": row.evidence_status,
                }
            )

        matches.append(
            {
                "shade_id": str(row.shade_id),
                "shade_code": row.shade_code,
                "shade_name": row.shade_name,
                "sub_range": row.sub_range_name,
                "brand": brand,
                "line": row.product_line_name,
                "line_id": str(row.line_id),
                "line_region_id": str(row.line_region_id),
                "canonical_key": row.canonical_key,
                "level": float(row.level) if row.level is not None else None,
                "normalized_tones": sorted(shade_tones),
                "match_score": score,
                "score_breakdown": breakdown,
                "provenance_links": provenance_links,
            }
        )

    matches.sort(
        key=lambda item: (
            -item["match_score"],
            item["brand"],
            item["line"],
            item["shade_code"],
        )
    )
    return matches


def lookup_shade_by_reference(
    session: Session,
    shade_ref: str,
    *,
    product_line_hint: str | None = None,
) -> dict[str, Any] | None:
    """Resolve a shade reference to a single best-matching imported shade row."""
    brand_hint, line_hint_from_ref, shade_code = parse_shade_reference(shade_ref)
    effective_line_hint = product_line_hint or line_hint_from_ref

    stmt = (
        select(
            Shade,
            Brand.brand_name.label("brand_name"),
            ProductLine.product_line_name.label("product_line_name"),
            ProductLine.line_id.label("line_id"),
            ProductLineRegion.canonical_key.label("canonical_key"),
            ProductLineRegion.line_region_id.label("line_region_id"),
            SubRange.sub_range_name.label("sub_range_name"),
        )
        .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
        .join(ProductLine, ProductLine.line_id == ProductLineRegion.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .outerjoin(SubRange, SubRange.sub_range_id == Shade.sub_range_id)
        .where(Shade.shade_code == shade_code)
        .where(Shade.is_active.is_(True))
        .order_by(ProductLine.product_line_name, SubRange.sub_range_name)
    )
    rows = session.execute(stmt).all()
    if not rows:
        return None

    filtered = rows
    if brand_hint:
        filtered = [row for row in rows if brand_matches(str(row.brand_name), brand_hint)]
        if not filtered:
            filtered = rows

    if effective_line_hint:
        line_filtered = [
            row
            for row in filtered
            if effective_line_hint.lower() in str(row.product_line_name).lower()
        ]
        if not line_filtered:
            return None
        filtered = line_filtered

    permanent = [
        row for row in filtered if _is_permanent_color_type(row[0].color_type)
    ]
    if permanent:
        filtered = permanent

    chosen = filtered[0]
    shade: Shade = chosen[0]
    tones_by_shade = _load_normalized_tones_for_shades(session, [shade.shade_id])

    return {
        "shade_id": shade.shade_id,
        "shade_code": shade.shade_code,
        "shade_name": shade.shade_name,
        "level": float(shade.level) if shade.level is not None else None,
        "color_type": shade.color_type,
        "gray_coverage_claim": shade.gray_coverage_claim,
        "brand": chosen.brand_name,
        "product_line": chosen.product_line_name,
        "line_id": chosen.line_id,
        "line_region_id": chosen.line_region_id,
        "canonical_key": chosen.canonical_key,
        "sub_range": chosen.sub_range_name,
        "normalized_tones": sorted(tones_by_shade.get(shade.shade_id, set())),
    }


def fetch_line_rules(session: Session, line_region_id: uuid.UUID) -> dict[str, Any]:
    """Fetch line technical rules keyed by rule_type for a product line region."""
    rows = session.scalars(
        select(LineTechnicalRule)
        .where(LineTechnicalRule.line_region_id == line_region_id)
        .order_by(LineTechnicalRule.rule_type)
    ).all()

    rules: dict[str, Any] = {}
    for row in rows:
        entry = {
            "value": row.rule_value,
            "source_url": row.source_url,
            "source_document": row.source_document,
            "source_confidence": row.source_confidence,
            "evidence_status": row.evidence_status,
            "assumptions": row.assumptions or [],
            "data_gaps": row.data_gaps or [],
        }
        rules.setdefault(row.rule_type, []).append(entry)
    return rules
