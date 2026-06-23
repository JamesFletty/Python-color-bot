"""Catalog queries for v2 PostgreSQL schema."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Brand, ProductLine, Shade
from app.schemas.catalog import BrandSummary, LineSummary, ShadeSummary


def list_brands(session: Session) -> list[BrandSummary]:
    rows = session.scalars(
        select(Brand)
        .options(joinedload(Brand.product_lines))
        .order_by(Brand.brand_name)
    ).unique().all()

    result: list[BrandSummary] = []
    for brand in rows:
        lines = sorted(brand.product_lines, key=lambda line: line.line_name)
        result.append(
            BrandSummary(
                brand_id=brand.brand_id,
                brand_name=brand.brand_name,
                lines=[
                    LineSummary(
                        line_id=line.line_id,
                        line_name=line.line_name,
                        canonical_key=line.canonical_key,
                        color_type=line.color_type,
                        region_or_market=line.region_or_market,
                    )
                    for line in lines
                ],
            )
        )
    return result


def list_shades_for_line(
    session: Session,
    line_id: int,
    *,
    query: str | None = None,
    limit: int = 100,
) -> list[ShadeSummary]:
    stmt = (
        select(Shade)
        .options(joinedload(Shade.tones))
        .where(Shade.line_id == line_id)
        .where(Shade.discontinued.is_(False))
        .order_by(Shade.shade_code)
        .limit(min(limit, 500))
    )
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Shade.shade_code.ilike(pattern),
                Shade.shade_name.ilike(pattern),
            )
        )

    shades = session.scalars(stmt).unique().all()
    return [
        ShadeSummary(
            shade_id=shade.shade_id,
            shade_code=shade.shade_code,
            shade_name=shade.shade_name,
            level=float(shade.level) if shade.level is not None else None,
            normalized_tones=[tone.tone_name for tone in shade.tones],
            sub_range=shade.sub_range,
            color_type=shade.color_type,
        )
        for shade in shades
    ]


def format_catalog_for_prompt(session: Session, line_id: int, *, limit: int = 80) -> str:
    shades = list_shades_for_line(session, line_id, limit=limit)
    lines = []
    for shade in shades:
        tone_text = ",".join(shade.normalized_tones) if shade.normalized_tones else ""
        level_text = f"L{shade.level:g}" if shade.level is not None else "L?"
        lines.append(f"- {shade.shade_code} ({level_text}, {tone_text})")
    return "\n".join(lines)


def get_line(session: Session, line_id: int) -> ProductLine | None:
    return session.get(ProductLine, line_id)
