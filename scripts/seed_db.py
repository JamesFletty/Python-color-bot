#!/usr/bin/env python3
"""Idempotent PostgreSQL seed loader from v2 CSV artifacts."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import get_engine, get_session_factory
from app.models import (
    Brand,
    CrossLineMapping,
    FormulationRule,
    ProductLine,
    Shade,
    ShadeTone,
)
from scripts.v2_paths import (
    BRANDS_LINES_CSV,
    CROSS_LINE_MAPPINGS_CSV,
    FORMULATION_RULES_CSV,
    SEED_DIR,
    SHADES_CSV,
)


@dataclass
class SeedSummary:
    brands: int = 0
    lines: int = 0
    shades: int = 0
    tones: int = 0
    rules: int = 0
    cross_line_mappings: int = 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_json_field(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def _is_discontinued(value: str) -> bool:
    lowered = (value or "").lower()
    return "discontinued" in lowered or lowered in {"inactive", "retired"}


def seed_brands_and_lines(session: Session) -> dict[str, int]:
    """Return canonical_key -> line_id mapping."""
    rows = _read_csv(BRANDS_LINES_CSV)
    brand_ids: dict[str, int] = {}
    line_ids: dict[str, int] = {}

    for row in rows:
        brand_name = row["brand_name"].strip()
        if brand_name not in brand_ids:
            stmt = (
                insert(Brand)
                .values(brand_name=brand_name)
                .on_conflict_do_update(
                    index_elements=[Brand.brand_name],
                    set_={"brand_name": brand_name},
                )
                .returning(Brand.brand_id)
            )
            brand_ids[brand_name] = session.scalar(stmt)

        canonical_key = row["canonical_key"].strip()
        stmt = (
            insert(ProductLine)
            .values(
                brand_id=brand_ids[brand_name],
                line_name=row["product_line_name"].strip(),
                canonical_key=canonical_key,
                color_type=row.get("line_category") or None,
                mixing_ratio_default=row.get("mixing_ratio_default") or None,
                developer_default_volume=int(row["developer_default_volume"])
                if row.get("developer_default_volume")
                else None,
                processing_time_default_minutes=int(row["processing_time_default_minutes"])
                if row.get("processing_time_default_minutes")
                else None,
                technical_defaults=_parse_json_field(row.get("technical_defaults_json", "")) or None,
                region_or_market=row.get("region_or_market") or None,
            )
            .on_conflict_do_update(
                index_elements=[ProductLine.canonical_key],
                set_={
                    "line_name": row["product_line_name"].strip(),
                    "color_type": row.get("line_category") or None,
                    "mixing_ratio_default": row.get("mixing_ratio_default") or None,
                    "developer_default_volume": int(row["developer_default_volume"])
                    if row.get("developer_default_volume")
                    else None,
                    "processing_time_default_minutes": int(row["processing_time_default_minutes"])
                    if row.get("processing_time_default_minutes")
                    else None,
                    "technical_defaults": _parse_json_field(row.get("technical_defaults_json", ""))
                    or None,
                    "region_or_market": row.get("region_or_market") or None,
                },
            )
            .returning(ProductLine.line_id)
        )
        line_ids[canonical_key] = session.scalar(stmt)

    session.flush()
    return line_ids


def seed_shades(session: Session, line_ids: dict[str, int]) -> tuple[int, int]:
    rows = _read_csv(SHADES_CSV)
    shade_count = 0
    tone_count = 0

    for row in rows:
        canonical_key = row["canonical_key"].strip()
        line_id = line_ids.get(canonical_key)
        if line_id is None:
            brand_name = row["brand"].strip()
            line_name = row["product_line"].strip()
            stmt = (
                insert(Brand)
                .values(brand_name=brand_name)
                .on_conflict_do_update(
                    index_elements=[Brand.brand_name],
                    set_={"brand_name": brand_name},
                )
                .returning(Brand.brand_id)
            )
            brand_id = session.scalar(stmt)
            stmt = (
                insert(ProductLine)
                .values(
                    brand_id=brand_id,
                    line_name=line_name,
                    canonical_key=canonical_key,
                    color_type=row.get("color_type") or None,
                )
                .on_conflict_do_update(
                    index_elements=[ProductLine.canonical_key],
                    set_={"line_name": line_name, "color_type": row.get("color_type") or None},
                )
                .returning(ProductLine.line_id)
            )
            line_id = session.scalar(stmt)
            line_ids[canonical_key] = line_id

        sub_range = row.get("sub_range") or ""
        metadata = _parse_json_field(row.get("metadata_json", ""))
        level_raw = row.get("level")
        level = float(level_raw) if level_raw else None

        stmt = (
            insert(Shade)
            .values(
                line_id=line_id,
                shade_code=row["shade_code"].strip(),
                shade_name=row.get("shade_name") or None,
                level=level,
                color_type=row.get("color_type") or None,
                sub_range=sub_range or None,
                mixing_ratio=row.get("mixing_ratio") or None,
                discontinued=_is_discontinued(row.get("discontinued_status", "")),
                gray_coverage_claim=row.get("gray_coverage_claim") or None,
                metadata_json=metadata or None,
            )
            .on_conflict_do_update(
                constraint="uq_shades_line_code_subrange",
                set_={
                    "shade_name": row.get("shade_name") or None,
                    "level": level,
                    "color_type": row.get("color_type") or None,
                    "mixing_ratio": row.get("mixing_ratio") or None,
                    "discontinued": _is_discontinued(row.get("discontinued_status", "")),
                    "gray_coverage_claim": row.get("gray_coverage_claim") or None,
                    "metadata_json": metadata or None,
                },
            )
            .returning(Shade.shade_id)
        )
        shade_id = session.scalar(stmt)
        shade_count += 1

        session.execute(delete(ShadeTone).where(ShadeTone.shade_id == shade_id))
        tones_raw = row.get("normalized_tones") or ""
        for position, tone in enumerate(t for t in tones_raw.split("|") if t):
            session.add(ShadeTone(shade_id=shade_id, tone_name=tone, position=position))
            tone_count += 1

    session.flush()
    return shade_count, tone_count


def seed_rules(session: Session, line_ids: dict[str, int]) -> int:
    rows = _read_csv(FORMULATION_RULES_CSV)
    count = 0
    for row in rows:
        canonical_key = (row.get("canonical_key") or "").strip()
        line_id = line_ids.get(canonical_key) if canonical_key else None
        stmt = (
            insert(FormulationRule)
            .values(
                package_rule_id=row["package_rule_id"].strip(),
                line_id=line_id,
                scope_level=row["scope_level"].strip(),
                rule_name=row["rule_name"].strip(),
                rule_priority=int(row.get("rule_priority") or 100),
                rule_category=row["rule_category"].strip(),
                evidence_status=row.get("evidence_status") or None,
                rule_condition=_parse_json_field(row.get("rule_condition_json", "")),
                rule_action=_parse_json_field(row.get("rule_action_json", "")),
                is_dormant=(row.get("is_dormant") or "").lower() == "true",
                is_active=True,
            )
            .on_conflict_do_update(
                index_elements=[FormulationRule.package_rule_id],
                set_={
                    "line_id": line_id,
                    "scope_level": row["scope_level"].strip(),
                    "rule_name": row["rule_name"].strip(),
                    "rule_priority": int(row.get("rule_priority") or 100),
                    "rule_category": row["rule_category"].strip(),
                    "evidence_status": row.get("evidence_status") or None,
                    "rule_condition": _parse_json_field(row.get("rule_condition_json", "")),
                    "rule_action": _parse_json_field(row.get("rule_action_json", "")),
                    "is_dormant": (row.get("is_dormant") or "").lower() == "true",
                    "is_active": True,
                },
            )
        )
        session.execute(stmt)
        count += 1
    session.flush()
    return count


def seed_cross_line(session: Session, line_ids: dict[str, int]) -> int:
    rows = _read_csv(CROSS_LINE_MAPPINGS_CSV)
    count = 0
    for row in rows:
        source_key = row["source_canonical_key"].strip()
        target_key = row["target_canonical_key"].strip()
        source_line_id = line_ids.get(source_key)
        target_line_id = line_ids.get(target_key)
        if source_line_id is None or target_line_id is None:
            continue
        role = row.get("component_role") or "base"
        stmt = (
            insert(CrossLineMapping)
            .values(
                conversion_id=row["conversion_id"].strip(),
                source_line_id=source_line_id,
                source_shade_code=row["source_shade_code"].strip(),
                target_line_id=target_line_id,
                target_shade_code=row["target_shade_code"].strip(),
                strategy=row.get("strategy") or None,
                confidence=row.get("mapping_confidence") or "exact",
                component_role=role,
                notes=row.get("notes") or None,
                source_document=row.get("source_document") or None,
            )
            .on_conflict_do_update(
                index_elements=[CrossLineMapping.conversion_id],
                set_={
                    "source_line_id": source_line_id,
                    "source_shade_code": row["source_shade_code"].strip(),
                    "target_line_id": target_line_id,
                    "target_shade_code": row["target_shade_code"].strip(),
                    "strategy": row.get("strategy") or None,
                    "confidence": row.get("mapping_confidence") or "exact",
                    "component_role": role,
                    "notes": row.get("notes") or None,
                    "source_document": row.get("source_document") or None,
                },
            )
        )
        session.execute(stmt)
        count += 1
    session.flush()
    return count


def run_seed(session: Session) -> SeedSummary:
    for path in (BRANDS_LINES_CSV, SHADES_CSV, FORMULATION_RULES_CSV, CROSS_LINE_MAPPINGS_CSV):
        if not path.exists():
            raise FileNotFoundError(f"Missing seed file: {path}")

    line_ids = seed_brands_and_lines(session)
    shade_count, tone_count = seed_shades(session, line_ids)
    rule_count = seed_rules(session, line_ids)
    mapping_count = seed_cross_line(session, line_ids)

    brand_count = session.scalar(select(func.count()).select_from(Brand)) or 0
    line_count = session.scalar(select(func.count()).select_from(ProductLine)) or 0

    return SeedSummary(
        brands=int(brand_count),
        lines=int(line_count),
        shades=shade_count,
        tones=tone_count,
        rules=rule_count,
        cross_line_mappings=mapping_count,
    )


def main() -> int:
    if not SEED_DIR.exists():
        print(f"Seed directory missing: {SEED_DIR}", file=sys.stderr)
        return 1

    get_engine()
    session = get_session_factory()()
    try:
        summary = run_seed(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(
        f"Seeded v2 catalog: {summary.brands} brands, {summary.lines} lines, "
        f"{summary.shades} shades, {summary.tones} tones, "
        f"{summary.rules} rules, {summary.cross_line_mappings} cross-line mappings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
