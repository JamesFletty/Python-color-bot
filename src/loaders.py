"""JSON loaders and SQLite population helpers."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.logging_utils import log_transformation
from src.paths import (
    EXPECTED_SHADE_COUNT,
    EXPECTED_TONE_MAPPING_COUNT,
    LINE_TECH_JSON,
    SHADES_JSON,
    TONE_MAP_JSON,
)
from src.schema import RULE_TYPE_FIELD_MAP

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


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON artifact from disk."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_level(value: Any) -> float | None:
    """Normalize shade level values to float."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def json_dumps(value: Any) -> str | None:
    """Serialize a value to JSON text for SQLite storage."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def get_or_create_brand(cursor: sqlite3.Cursor, brand_name: str) -> int:
    """Return brand_id, inserting the brand when missing."""
    cursor.execute(
        "INSERT OR IGNORE INTO brand (brand_name) VALUES (?)",
        (brand_name,),
    )
    cursor.execute("SELECT brand_id FROM brand WHERE brand_name = ?", (brand_name,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to resolve brand_id for {brand_name!r}")
    return int(row[0])


def get_or_create_line(
    cursor: sqlite3.Cursor,
    *,
    brand_name: str,
    product_line: str,
    canonical_key: str,
    color_type: str | None = None,
    region_or_market: str | None = None,
    discontinued_status: str | None = None,
) -> int:
    """Return product_line.line_id, inserting when missing."""
    brand_id = get_or_create_brand(cursor, brand_name)
    cursor.execute(
        """
        INSERT OR IGNORE INTO product_line (
            brand_id, product_line_name, canonical_key, color_type,
            region_or_market, discontinued_status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            product_line,
            canonical_key,
            color_type,
            region_or_market,
            discontinued_status,
        ),
    )
    cursor.execute(
        """
        SELECT line_id FROM product_line
        WHERE brand_id = ? AND product_line_name = ?
        """,
        (brand_id, product_line),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to resolve line_id for {canonical_key!r}")
    return int(row[0])


def infer_sub_range(record: dict[str, Any]) -> str:
    """Derive sub-range label for shades that share a code within a line."""
    mixing_ratio = record.get("mixing_ratio") or ""
    gray_claim = record.get("gray_coverage_claim") or ""
    special = record.get("special_usage_notes") or ""
    blob = f"{mixing_ratio} {gray_claim} {special}"

    if "Extra Coverage" in blob:
        return "Extra Coverage"
    if "DreamAge" in blob:
        return "DreamAge"
    if "10 min" in mixing_ratio or "Pre-Bonded" in mixing_ratio:
        return "Pre-Bonded 10 min"
    return ""


def load_shades(
    conn: sqlite3.Connection,
    logger: logging.Logger,
    shades_path: Path = SHADES_JSON,
) -> int:
    """Load normalized shade records into SQLite."""
    payload = load_json(shades_path)
    records = payload["normalized_shade_records"]
    cursor = conn.cursor()
    inserted = 0

    for record in records:
        line_id = get_or_create_line(
            cursor,
            brand_name=record["brand"],
            product_line=record["product_line"],
            canonical_key=record["canonical_key"],
            color_type=record.get("color_type"),
            region_or_market=record.get("region_or_market"),
            discontinued_status=record.get("discontinued_status"),
        )
        cursor.execute(
            """
            INSERT OR REPLACE INTO shade (
                line_id, canonical_key, shade_code, shade_name, sub_range, level, color_type,
                gray_coverage_claim, lift_levels, mixing_ratio, developer_options,
                processing_time_minutes, special_usage_notes, manufacturer_tone_codes,
                manufacturer_tone_descriptions, region_or_market, discontinued_status,
                source_url, source_document, source_type, source_publication_date,
                source_confidence, evidence_status, assumptions, data_gaps
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                line_id,
                record["canonical_key"],
                record["shade_code"],
                record.get("shade_name"),
                (record.get("sub_range") or infer_sub_range(record) or ""),
                parse_level(record.get("level")),
                record.get("color_type"),
                record.get("gray_coverage_claim"),
                record.get("lift_levels"),
                record.get("mixing_ratio"),
                json_dumps(record.get("developer_options")),
                record.get("processing_time_minutes"),
                record.get("special_usage_notes"),
                json_dumps(record.get("manufacturer_tone_codes")),
                json_dumps(record.get("manufacturer_tone_descriptions")),
                record.get("region_or_market"),
                record.get("discontinued_status"),
                record.get("source_url"),
                record.get("source_document"),
                record.get("source_type"),
                record.get("source_publication_date"),
                record.get("source_confidence"),
                record.get("evidence_status"),
                json_dumps(record.get("assumptions")),
                json_dumps(record.get("data_gaps")),
            ),
        )
        shade_id = cursor.lastrowid
        cursor.execute(
            "DELETE FROM shade_normalized_tone WHERE shade_id = ?",
            (shade_id,),
        )
        for position, tone in enumerate(record.get("normalized_tones") or [], start=1):
            if tone not in VALID_TONES:
                log_transformation(
                    logger,
                    "invalid_normalized_tone_skipped",
                    {"shade_code": record["shade_code"], "tone": tone},
                )
                continue
            cursor.execute(
                """
                INSERT INTO shade_normalized_tone (shade_id, tone_name, position)
                VALUES (?, ?, ?)
                """,
                (shade_id, tone, position),
            )
        inserted += 1

    conn.commit()
    log_transformation(
        logger,
        "load_shades_complete",
        {"source": str(shades_path), "records_processed": inserted},
    )
    return inserted


def load_tone_mappings(
    conn: sqlite3.Connection,
    logger: logging.Logger,
    tone_map_path: Path = TONE_MAP_JSON,
) -> int:
    """Load tone normalization mappings into SQLite."""
    payload = load_json(tone_map_path)
    mappings = payload["tone_normalization_map"]
    cursor = conn.cursor()
    inserted = 0

    for mapping in mappings:
        line_id = get_or_create_line(
            cursor,
            brand_name=mapping["brand"],
            product_line=mapping["product_line"],
            canonical_key=mapping["canonical_key"],
        )
        cursor.execute(
            """
            INSERT OR REPLACE INTO tone_normalization (
                line_id, canonical_key, manufacturer_tone_code, manufacturer_term,
                normalized_tones, mapping_rationale, mapping_confidence,
                ambiguity_flag, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                line_id,
                mapping["canonical_key"],
                mapping["manufacturer_tone_code"],
                mapping.get("manufacturer_term"),
                json_dumps(mapping.get("normalized_tones") or []),
                mapping.get("mapping_rationale"),
                mapping.get("mapping_confidence"),
                1 if mapping.get("ambiguity_flag") else 0,
                json_dumps(mapping.get("notes")),
            ),
        )
        inserted += 1

    conn.commit()
    log_transformation(
        logger,
        "load_tone_mappings_complete",
        {"source": str(tone_map_path), "records_processed": inserted},
    )
    return inserted


def load_line_technical_rules(
    conn: sqlite3.Connection,
    logger: logging.Logger,
    line_tech_path: Path = LINE_TECH_JSON,
) -> int:
    """Expand line technical records into typed line_technical_rule rows."""
    payload = load_json(line_tech_path)
    records = payload["line_technical_records"]
    cursor = conn.cursor()
    inserted = 0

    for record in records:
        line_id = get_or_create_line(
            cursor,
            brand_name=record["brand"],
            product_line=record["product_line"],
            canonical_key=record["canonical_key"],
            color_type=record.get("color_type"),
            region_or_market=record.get("region_or_market"),
            discontinued_status=record.get("discontinued_status"),
        )
        cursor.execute(
            "DELETE FROM line_technical_rule WHERE line_id = ?",
            (line_id,),
        )

        provenance = {
            "source_url": record.get("source_url"),
            "source_document": record.get("source_document"),
            "source_confidence": record.get("source_confidence"),
            "evidence_status": record.get("evidence_status"),
            "assumptions": record.get("assumptions"),
            "data_gaps": record.get("data_gaps"),
        }

        for field_name, rule_type in RULE_TYPE_FIELD_MAP.items():
            value = record.get(field_name)
            if value is None:
                continue
            if isinstance(value, list) and not value:
                continue
            if isinstance(value, str) and not value.strip():
                continue

            cursor.execute(
                """
                INSERT INTO line_technical_rule (
                    line_id, canonical_key, rule_type, rule_value,
                    source_url, source_document, source_confidence,
                    evidence_status, assumptions, data_gaps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    line_id,
                    record["canonical_key"],
                    rule_type,
                    json_dumps(value),
                    provenance["source_url"],
                    provenance["source_document"],
                    provenance["source_confidence"],
                    provenance["evidence_status"],
                    json_dumps(provenance["assumptions"]),
                    json_dumps(provenance["data_gaps"]),
                ),
            )
            inserted += 1

    conn.commit()
    log_transformation(
        logger,
        "load_line_technical_rules_complete",
        {"source": str(line_tech_path), "rule_rows_inserted": inserted},
    )
    return inserted


def validate_counts(conn: sqlite3.Connection) -> dict[str, Any]:
    """Validate loaded row counts against expected package totals."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM shade")
    shade_count = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM tone_normalization")
    tone_count = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM line_technical_rule")
    rule_count = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM product_line")
    line_count = int(cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM brand")
    brand_count = int(cursor.fetchone()[0])

    return {
        "shade_count": shade_count,
        "tone_mapping_count": tone_count,
        "line_technical_rule_count": rule_count,
        "product_line_count": line_count,
        "brand_count": brand_count,
        "expected_shade_count": EXPECTED_SHADE_COUNT,
        "expected_tone_mapping_count": EXPECTED_TONE_MAPPING_COUNT,
        "shade_count_ok": shade_count == EXPECTED_SHADE_COUNT,
        "tone_mapping_count_ok": tone_count == EXPECTED_TONE_MAPPING_COUNT,
    }
