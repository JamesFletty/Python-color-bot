"""Import Stage 12 research package JSON into PostgreSQL research tables."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.loaders import infer_sub_range, load_json, parse_level
from src.paths import (
    EXPECTED_SHADE_COUNT,
    EXPECTED_TONE_MAPPING_COUNT,
    LINE_TECH_JSON,
    SHADES_JSON,
    TONE_MAP_JSON,
)
from src.schema import RULE_TYPE_FIELD_MAP

from .production_models import (
    Brand,
    IngestionRun,
    LineTechnicalRule,
    NormalizedTone,
    ProductLine,
    ProductLineRegion,
    Shade,
    ShadeRaw,
    SourceDocument,
    SubRange,
    ToneCodeReference,
    ToneNormalization,
)

STAGE12_BATCH_LABEL = "stage12_package_v1"
RESEARCH_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
DEFAULT_SUB_RANGE = "Standard"
VALID_TONES = frozenset(
    {
        "Natural",
        "Neutral",
        "Ash",
        "Blue",
        "Green",
        "Violet",
        "Pearl",
        "Gold",
        "Beige",
        "Copper",
        "Red",
        "Mahogany",
        "Mocha",
        "Brown",
        "Warm",
        "Cool",
        "Other",
    }
)


@dataclass
class Stage12ImportSummary:
    shades: int = 0
    tone_mappings: int = 0
    line_technical_rules: int = 0
    brands: int = 0
    lines: int = 0
    regions: int = 0


def deterministic_id(key: str) -> uuid.UUID:
    """Stable UUID for a research-layer natural key."""
    return uuid.uuid5(RESEARCH_NAMESPACE, key)


def _brand_id(brand_name: str) -> uuid.UUID:
    return deterministic_id(f"brand:{brand_name}")


def _line_id(brand_name: str, product_line: str) -> uuid.UUID:
    return deterministic_id(f"line:{brand_name}::{product_line}")


def _region_id(canonical_key: str) -> uuid.UUID:
    return deterministic_id(f"region:{canonical_key}")


def _sub_range_id(canonical_key: str, sub_range_name: str) -> uuid.UUID:
    return deterministic_id(f"subrange:{canonical_key}::{sub_range_name}")


def _shade_id(canonical_key: str, sub_range_name: str, shade_code: str) -> uuid.UUID:
    return deterministic_id(f"shade:{canonical_key}::{sub_range_name}::{shade_code}")


def _shade_raw_id(canonical_key: str, sub_range_name: str, shade_code: str) -> uuid.UUID:
    return deterministic_id(
        f"shade_raw:{STAGE12_BATCH_LABEL}:{canonical_key}::{sub_range_name}::{shade_code}"
    )


def _source_id(source_url: str | None, fallback: str) -> uuid.UUID:
    return deterministic_id(f"source:{source_url or fallback}")


def _tone_code_id(canonical_key: str, manufacturer_tone_code: str) -> uuid.UUID:
    return deterministic_id(f"tone_code:{canonical_key}::{manufacturer_tone_code}")


def _normalized_tone_id(tone_name: str) -> uuid.UUID:
    return deterministic_id(f"normalized_tone:{tone_name}")


def _line_technical_rule_id(canonical_key: str, rule_type: str) -> uuid.UUID:
    return deterministic_id(f"ltr:{canonical_key}::{rule_type}")


def _ingestion_run_id() -> uuid.UUID:
    return deterministic_id(f"ingestion_run:{STAGE12_BATCH_LABEL}")


def _json_ready(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    return value


def ensure_ingestion_run(session: Session) -> uuid.UUID:
    run_id = _ingestion_run_id()
    session.merge(
        IngestionRun(
            ingestion_run_id=run_id,
            batch_label=STAGE12_BATCH_LABEL,
            tooling_version="import_stage12_research.py",
            notes="Deterministic import from stage12_package JSON artifacts",
        )
    )
    return run_id


def upsert_brand_line_region(
    session: Session,
    *,
    brand_name: str,
    product_line: str,
    canonical_key: str,
    region_or_market: str | None = None,
    line_category: str | None = None,
    discontinued_status: str | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Ensure brand → line → region hierarchy exists; return their UUIDs."""
    bid = _brand_id(brand_name)
    lid = _line_id(brand_name, product_line)
    rid = _region_id(canonical_key)

    session.merge(Brand(brand_id=bid, brand_name=brand_name))
    session.merge(
        ProductLine(
            line_id=lid,
            brand_id=bid,
            product_line_name=product_line,
            line_category=line_category,
        )
    )
    session.merge(
        ProductLineRegion(
            line_region_id=rid,
            line_id=lid,
            region_or_market=region_or_market or "US",
            canonical_key=canonical_key,
            discontinued_status=discontinued_status,
        )
    )
    return bid, lid, rid


def upsert_sub_range(
    session: Session, *, line_region_id: uuid.UUID, canonical_key: str, sub_range_name: str
) -> uuid.UUID:
    sub_id = _sub_range_id(canonical_key, sub_range_name)
    session.merge(
        SubRange(
            sub_range_id=sub_id,
            line_region_id=line_region_id,
            sub_range_name=sub_range_name,
        )
    )
    return sub_id


def upsert_source_from_record(session: Session, record: dict[str, Any]) -> uuid.UUID:
    canonical_key = str(record.get("canonical_key", "unknown"))
    source_url = record.get("source_url")
    sid = _source_id(source_url, canonical_key)
    session.merge(
        SourceDocument(
            source_id=sid,
            source_title=str(record.get("source_document") or record.get("source_title") or canonical_key)[:500],
            source_type=record.get("source_type"),
            source_url=source_url,
            publication_or_revision_date=record.get("source_publication_date"),
            access_status="public",
            source_priority_tier=1,
            region_or_market=record.get("region_or_market"),
            retrieved_at=datetime.now(timezone.utc),
        )
    )
    return sid


def import_normalized_shade(
    session: Session,
    record: dict[str, Any],
    *,
    ingestion_run_id: uuid.UUID,
) -> uuid.UUID:
    """Append shade_raw (idempotent key) and rebuild shade row deterministically."""
    canonical_key = str(record["canonical_key"])
    shade_code = str(record["shade_code"])
    sub_range_name = infer_sub_range(record) or DEFAULT_SUB_RANGE

    _, _, line_region_id = upsert_brand_line_region(
        session,
        brand_name=str(record["brand"]),
        product_line=str(record["product_line"]),
        canonical_key=canonical_key,
        region_or_market=record.get("region_or_market"),
        line_category=record.get("color_type"),
        discontinued_status=record.get("discontinued_status"),
    )
    sub_range_id = upsert_sub_range(
        session,
        line_region_id=line_region_id,
        canonical_key=canonical_key,
        sub_range_name=sub_range_name,
    )
    source_id = upsert_source_from_record(session, record)

    shade_raw_id = _shade_raw_id(canonical_key, sub_range_name, shade_code)
    shade_id = _shade_id(canonical_key, sub_range_name, shade_code)
    level = parse_level(record.get("level"))

    session.merge(
        ShadeRaw(
            shade_raw_id=shade_raw_id,
            line_region_id=line_region_id,
            sub_range_id=sub_range_id,
            shade_code_raw=shade_code,
            shade_name_raw=record.get("shade_name"),
            level_raw=Decimal(str(level)) if level is not None else None,
            tone_codes_raw=_json_ready(record.get("manufacturer_tone_codes")),
            tone_descriptions_raw=_json_ready(record.get("manufacturer_tone_descriptions")),
            gray_coverage_claim_raw=record.get("gray_coverage_claim"),
            lift_capability_raw=record.get("lift_levels"),
            mixing_ratio_raw=record.get("mixing_ratio"),
            developer_recommendations_raw=_json_ready(record.get("developer_options")),
            processing_time_raw=str(record.get("processing_time_minutes"))
            if record.get("processing_time_minutes") is not None
            else None,
            special_usage_notes_raw=record.get("special_usage_notes"),
            official_swatch_image_exists=record.get("official_swatch_image_exists"),
            source_id=source_id,
            source_confidence=record.get("source_confidence"),
            evidence_status=record.get("evidence_status"),
            assumptions=_json_ready(record.get("assumptions")),
            data_gaps=_json_ready(record.get("data_gaps")),
            ingestion_run_id=ingestion_run_id,
        )
    )

    mixing_inherited = any(
        "inherited from line" in str(item).lower()
        for item in (record.get("assumptions") or [])
    )

    session.merge(
        Shade(
            shade_id=shade_id,
            shade_raw_id=shade_raw_id,
            line_region_id=line_region_id,
            sub_range_id=sub_range_id,
            shade_code=shade_code,
            shade_name=record.get("shade_name"),
            level=Decimal(str(level)) if level is not None else None,
            color_type=record.get("color_type"),
            gray_coverage_claim=record.get("gray_coverage_claim"),
            lift_levels=record.get("lift_levels"),
            mixing_ratio=record.get("mixing_ratio"),
            mixing_ratio_inherited=mixing_inherited,
            processing_time_minutes=record.get("processing_time_minutes"),
            processing_time_inherited=False,
            is_active=True,
        )
    )

    for tone_name in record.get("normalized_tones") or []:
        if tone_name not in VALID_TONES:
            continue
        session.merge(
            NormalizedTone(
                normalized_tone_id=_normalized_tone_id(str(tone_name)),
                tone_name=str(tone_name),
            )
        )

    return shade_id


def import_tone_normalization_map(session: Session) -> int:
    payload = load_json(TONE_MAP_JSON)
    mappings = payload["tone_normalization_map"]
    count = 0

    for mapping in mappings:
        canonical_key = str(mapping["canonical_key"])
        manufacturer_tone_code = str(mapping["manufacturer_tone_code"])
        _, _, line_region_id = upsert_brand_line_region(
            session,
            brand_name=str(mapping["brand"]),
            product_line=str(mapping["product_line"]),
            canonical_key=canonical_key,
        )
        tone_code_id = _tone_code_id(canonical_key, manufacturer_tone_code)
        session.merge(
            ToneCodeReference(
                tone_code_id=tone_code_id,
                line_region_id=line_region_id,
                manufacturer_tone_code=manufacturer_tone_code,
                manufacturer_term=mapping.get("manufacturer_term"),
                manufacturer_definition=mapping.get("mapping_rationale"),
                confidence=mapping.get("mapping_confidence"),
                notes_on_ambiguity=_json_ready(mapping.get("notes")),
            )
        )
        for tone_name in mapping.get("normalized_tones") or []:
            if tone_name not in VALID_TONES:
                continue
            normalized_tone_id = _normalized_tone_id(str(tone_name))
            session.merge(
                NormalizedTone(
                    normalized_tone_id=normalized_tone_id,
                    tone_name=str(tone_name),
                )
            )
            session.merge(
                ToneNormalization(
                    tone_code_id=tone_code_id,
                    normalized_tone_id=normalized_tone_id,
                    mapping_rationale=mapping.get("mapping_rationale"),
                    mapping_confidence=mapping.get("mapping_confidence"),
                    ambiguity_flag=bool(mapping.get("ambiguity_flag")),
                )
            )
        count += 1

    return count


def import_line_technical_records(session: Session) -> int:
    payload = load_json(LINE_TECH_JSON)
    records = payload["line_technical_records"]
    inserted = 0

    for record in records:
        canonical_key = str(record["canonical_key"])
        _, _, line_region_id = upsert_brand_line_region(
            session,
            brand_name=str(record["brand"]),
            product_line=str(record["product_line"]),
            canonical_key=canonical_key,
            region_or_market=record.get("region_or_market"),
            line_category=record.get("color_type"),
            discontinued_status=record.get("discontinued_status"),
        )
        source_id = upsert_source_from_record(session, record)

        session.execute(
            delete(LineTechnicalRule).where(
                LineTechnicalRule.line_region_id == line_region_id
            )
        )

        for field_name, rule_type in RULE_TYPE_FIELD_MAP.items():
            value = record.get(field_name)
            if value is None:
                continue
            if isinstance(value, list) and not value:
                continue
            if isinstance(value, str) and not value.strip():
                continue

            if isinstance(value, dict):
                rule_payload: dict[str, Any] | list[Any] = value
            elif isinstance(value, list):
                rule_payload = value
            else:
                rule_payload = {"value": value}

            rule_id = _line_technical_rule_id(canonical_key, rule_type)
            session.merge(
                LineTechnicalRule(
                    rule_id=rule_id,
                    line_region_id=line_region_id,
                    rule_type=rule_type,
                    rule_value=rule_payload,
                    source_id=source_id,
                    source_confidence=record.get("source_confidence"),
                    evidence_status=record.get("evidence_status"),
                )
            )
            inserted += 1

    return inserted


def validate_import_counts(session: Session) -> dict[str, Any]:
    shade_count = session.scalar(select(func.count()).select_from(Shade)) or 0
    tone_count = session.scalar(select(func.count()).select_from(ToneNormalization)) or 0
    rule_count = session.scalar(select(func.count()).select_from(LineTechnicalRule)) or 0
    brand_count = session.scalar(select(func.count()).select_from(Brand)) or 0
    line_count = session.scalar(select(func.count()).select_from(ProductLine)) or 0
    region_count = session.scalar(select(func.count()).select_from(ProductLineRegion)) or 0

    return {
        "shade_count": int(shade_count),
        "tone_mapping_count": int(tone_count),
        "line_technical_rule_count": int(rule_count),
        "brand_count": int(brand_count),
        "product_line_count": int(line_count),
        "product_line_region_count": int(region_count),
        "expected_shade_count": EXPECTED_SHADE_COUNT,
        "expected_tone_mapping_count": EXPECTED_TONE_MAPPING_COUNT,
        "shade_count_ok": int(shade_count) == EXPECTED_SHADE_COUNT,
        "tone_mapping_count_ok": int(tone_count) == EXPECTED_TONE_MAPPING_COUNT,
    }


def import_stage12_research(session: Session) -> Stage12ImportSummary:
    """Load Stage 12 package JSON into PostgreSQL research tables (idempotent)."""
    ingestion_run_id = ensure_ingestion_run(session)
    shades_payload = load_json(SHADES_JSON)
    shade_records = shades_payload["normalized_shade_records"]

    for record in shade_records:
        import_normalized_shade(session, record, ingestion_run_id=ingestion_run_id)

    tone_mappings = import_tone_normalization_map(session)
    line_rules = import_line_technical_records(session)
    session.flush()

    counts = validate_import_counts(session)
    return Stage12ImportSummary(
        shades=counts["shade_count"],
        tone_mappings=tone_mappings,
        line_technical_rules=line_rules,
        brands=counts["brand_count"],
        lines=counts["product_line_count"],
        regions=counts["product_line_region_count"],
    )


def find_shade_id(
    session: Session,
    *,
    canonical_key: str,
    shade_code: str,
    sub_range_name: str = DEFAULT_SUB_RANGE,
) -> uuid.UUID | None:
    """Lookup imported shade UUID by canonical key and shade code."""
    sub_range_id = _sub_range_id(canonical_key, sub_range_name)
    line_region_id = _region_id(canonical_key)
    return session.scalar(
        select(Shade.shade_id).where(
            Shade.line_region_id == line_region_id,
            Shade.sub_range_id == sub_range_id,
            Shade.shade_code == shade_code,
        )
    )


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os
    import sys

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    parser = argparse.ArgumentParser(description="Import Stage 12 research package into PostgreSQL")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    engine = create_engine(args.database_url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        summary = import_stage12_research(session)
        report = validate_import_counts(session)
        session.commit()
        print(
            f"Imported {summary.shades} shades, {summary.tone_mappings} tone mappings, "
            f"{summary.line_technical_rules} line technical rules."
        )
        print(json.dumps(report, indent=2))
        if not report["shade_count_ok"] or not report["tone_mapping_count_ok"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
