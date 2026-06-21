"""PostgreSQL catalog lookups for brands, lines, and shades."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from hair_color_db.production.production_models import (
    Brand,
    ProductLine,
    ProductLineRegion,
    Shade,
    SubRange,
)


def _line_color_type(session: Session, line_id: uuid.UUID) -> str | None:
    return session.scalar(
        select(Shade.color_type)
        .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
        .where(ProductLineRegion.line_id == line_id, Shade.color_type.is_not(None))
        .limit(1)
    )


def get_brands_and_lines(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            Brand.brand_id,
            Brand.brand_name,
            ProductLine.line_id,
            ProductLine.product_line_name,
            ProductLineRegion.canonical_key,
        )
        .join(ProductLine, ProductLine.brand_id == Brand.brand_id)
        .join(ProductLineRegion, ProductLineRegion.line_id == ProductLine.line_id)
        .order_by(Brand.brand_name, ProductLine.product_line_name, ProductLineRegion.region_or_market)
    ).all()

    brands: dict[str, dict[str, Any]] = {}
    seen_lines: set[str] = set()
    for brand_id, brand_name, line_id, line_name, canonical_key in rows:
        brand_key = str(brand_id)
        if brand_key not in brands:
            brands[brand_key] = {"id": brand_key, "name": brand_name, "lines": []}
        line_key = str(line_id)
        if line_key in seen_lines:
            continue
        seen_lines.add(line_key)
        brands[brand_key]["lines"].append(
            {
                "id": line_key,
                "name": line_name,
                "key": canonical_key,
                "color_type": _line_color_type(session, line_id),
            }
        )
    return list(brands.values())


def get_line_by_id(session: Session, line_id: str) -> dict[str, Any] | None:
    try:
        parsed_line_id = uuid.UUID(line_id)
    except ValueError:
        return None

    row = session.execute(
        select(
            ProductLine.line_id,
            ProductLine.product_line_name,
            ProductLineRegion.canonical_key,
            Brand.brand_name,
        )
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .join(ProductLineRegion, ProductLineRegion.line_id == ProductLine.line_id)
        .where(ProductLine.line_id == parsed_line_id)
        .limit(1)
    ).first()
    if row is None:
        return None
    return {
        "id": str(row.line_id),
        "name": row.product_line_name,
        "key": row.canonical_key,
        "color_type": _line_color_type(session, row.line_id),
        "brand": row.brand_name,
    }


def search_shades(
    session: Session,
    *,
    line_id: str | None = None,
    query: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    stmt = (
        select(
            Shade.shade_id,
            Shade.shade_code,
            Shade.shade_name,
            Shade.level,
            Shade.color_type,
            Shade.mixing_ratio,
            ProductLine.product_line_name,
            Brand.brand_name,
            SubRange.sub_range_name,
        )
        .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
        .join(ProductLine, ProductLine.line_id == ProductLineRegion.line_id)
        .join(Brand, Brand.brand_id == ProductLine.brand_id)
        .outerjoin(SubRange, SubRange.sub_range_id == Shade.sub_range_id)
        .where(Shade.is_active.is_(True))
    )

    if line_id is not None:
        try:
            parsed_line_id = uuid.UUID(line_id)
        except ValueError:
            return []
        stmt = stmt.where(ProductLine.line_id == parsed_line_id)

    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Shade.shade_code.ilike(pattern), Shade.shade_name.ilike(pattern)))

    stmt = stmt.order_by(Shade.level, Shade.shade_code).limit(limit)
    return [
        {
            "id": str(row.shade_id),
            "code": row.shade_code,
            "name": row.shade_name,
            "level": float(row.level) if row.level is not None else None,
            "color_type": row.color_type,
            "sub_range": row.sub_range_name,
            "mixing_ratio": row.mixing_ratio,
            "line": row.product_line_name,
            "brand": row.brand_name,
        }
        for row in session.execute(stmt).all()
    ]
