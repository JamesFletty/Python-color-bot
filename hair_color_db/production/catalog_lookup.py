"""Resolve catalog UUIDs from imported PostgreSQL research tables."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from .import_stage12_research import (
    DEFAULT_SUB_RANGE,
    _brand_id,
    _line_id,
    _region_id,
    find_shade_id,
)
from .shade_matching import lookup_shade_by_reference


@dataclass(frozen=True)
class CatalogReference:
    """IDs needed to run the production engine for one shade."""

    canonical_key: str
    shade_code: str
    brand_id: uuid.UUID
    line_id: uuid.UUID
    line_region_id: uuid.UUID
    shade_id: uuid.UUID
    sub_range_name: str = DEFAULT_SUB_RANGE


def parse_canonical_key(canonical_key: str) -> tuple[str, str, str]:
    """Parse ``Brand::Line::Region`` into components."""
    parts = canonical_key.split("::")
    if len(parts) != 3:
        raise ValueError(f"Expected Brand::Line::Region, got {canonical_key!r}")
    return parts[0], parts[1], parts[2]


def resolve_catalog_reference(
    session: Session,
    *,
    canonical_key: str,
    shade_code: str,
    sub_range_name: str = DEFAULT_SUB_RANGE,
) -> CatalogReference:
    """Lookup deterministic catalog UUIDs for a shade reference."""
    brand_name, line_name, _region = parse_canonical_key(canonical_key)
    brand_id = _brand_id(brand_name)
    line_id = _line_id(brand_name, line_name)
    line_region_id = _region_id(canonical_key)
    shade_id = find_shade_id(
        session,
        canonical_key=canonical_key,
        shade_code=shade_code,
        sub_range_name=sub_range_name,
    )
    if shade_id is None:
        raise LookupError(
            f"Shade {shade_code!r} not found for {canonical_key!r} "
            f"(sub-range {sub_range_name!r}). Run import_stage12_research first."
        )
    return CatalogReference(
        canonical_key=canonical_key,
        shade_code=shade_code,
        brand_id=brand_id,
        line_id=line_id,
        line_region_id=line_region_id,
        shade_id=shade_id,
        sub_range_name=sub_range_name,
    )


def resolve_from_shade_reference(
    session: Session,
    shade_ref: str,
    *,
    product_line_hint: str | None = None,
) -> CatalogReference:
    """Resolve a free-form shade reference via search/lookup."""
    row = lookup_shade_by_reference(
        session,
        shade_ref,
        product_line_hint=product_line_hint,
    )
    if row is None:
        raise LookupError(f"Shade reference not found: {shade_ref!r}")

    brand_name = str(row["brand"])
    return CatalogReference(
        canonical_key=str(row["canonical_key"]),
        shade_code=str(row["shade_code"]),
        brand_id=_brand_id(brand_name),
        line_id=row["line_id"],
        line_region_id=row["line_region_id"],
        shade_id=row["shade_id"],
        sub_range_name=str(row.get("sub_range") or DEFAULT_SUB_RANGE),
    )
