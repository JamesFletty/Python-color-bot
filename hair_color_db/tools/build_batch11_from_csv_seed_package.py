#!/usr/bin/env python3
"""Convert v5 Schwarzkopf IGORA ROYAL CSV seed package to Stage 12 batch artifacts."""

from __future__ import annotations

import csv
import json
import os
import sys
from typing import Any

TOOLS = os.path.dirname(__file__)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from seed_package_builder import (
    build_line_technical_records,
    build_shade_record,
    build_tone_maps,
    line_key,
    source_lookup,
    write_batch_artifacts,
)
from seed_package_mappings import LINE_MAP

BASE = os.path.join(TOOLS, "..")
B11 = os.path.join(BASE, "batches", "batch11")

COLOR_TYPE_BY_CATEGORY = {
    "permanent": "permanent",
    "highlift": "permanent",
    "pastel": "permanent",
    "highlight_color": "permanent",
    "modifier": "additive",
}


def _read_csv(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parse_json_field(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _sources_from_csv(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for row in rows:
        sources.append(
            {
                "source_key": row["source_key"],
                "brand": row["brand"],
                "document_filename": row["document_filename"],
                "page_start": int(row["page_start"]),
                "page_end": int(row["page_end"]),
                "source_label": row["source_label"],
                "source_tier": row["source_tier"],
                "access_status": row["access_status"],
            }
        )
    return sources


def _technical_rules_from_csv(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for row in rows:
        rules.append(
            {
                "brand": row["brand"],
                "product_line": row["product_line"] or None,
                "rule_category": row["rule_category"],
                "rule_name": row["rule_name"],
                "rule_condition": _parse_json_field(row["rule_condition"]),
                "rule_action": _parse_json_field(row["rule_action"]),
                "source_key": row["source_key"],
            }
        )
    return rules


def _shade_seed_from_csv(row: dict[str, str]) -> dict[str, Any]:
    level = row.get("level") or ""
    return {
        "brand": row["brand"],
        "product_line": row["product_line"],
        "sub_range": row.get("sub_range") or None,
        "shade_code": row["shade_code"],
        "display_code": row.get("display_code"),
        "shade_name": row.get("shade_name") or None,
        "level": float(level) if level else None,
        "tone_code": row.get("tone_code") or None,
        "shade_category": row.get("shade_category") or None,
        "source_key": row["source_key"],
        "evidence_status": row.get("evidence_status", "manufacturer_stated"),
        "confidence": row.get("confidence", "confirmed"),
    }


def _formula_recreation_rules(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for row in rows:
        rules.append(
            {
                "brand": row["brand"],
                "product_line": row["product_line"],
                "previous_shade_code": row["previous_shade_code"],
                "recreation_formula_text": row.get("recreation_formula_text"),
                "mixing_possible": row.get("mixing_possible", "").lower() == "true",
                "ratio": row.get("ratio") or None,
                "components": _parse_json_field(row.get("components_json")),
                "developer_grams": float(row["developer_grams"]) if row.get("developer_grams") else None,
                "source_key": row["source_key"],
                "evidence_status": row.get("evidence_status", "manufacturer_stated"),
            }
        )
    return rules


def main() -> None:
    shade_rows = _read_csv(os.path.join(B11, "normalized_shades.csv"))
    tech_rows = _read_csv(os.path.join(B11, "normalized_technical_rules.csv"))
    recreation_rows = _read_csv(os.path.join(B11, "formula_recreation_rules.csv"))
    source_rows = _read_csv(os.path.join(B11, "source_documents.csv"))

    sources_by_key = source_lookup(_sources_from_csv(source_rows))
    normalized: list[dict[str, Any]] = []

    for row in shade_rows:
        seed_shade = _shade_seed_from_csv(row)
        cfg = dict(LINE_MAP[line_key(seed_shade["brand"], seed_shade["product_line"])])
        category = seed_shade.get("shade_category")
        if category in COLOR_TYPE_BY_CATEGORY:
            cfg["color_type"] = COLOR_TYPE_BY_CATEGORY[category]
        record = build_shade_record(seed_shade, cfg, sources_by_key, batch_label="batch11")
        record["assumptions"] = [
            "Converted from v5 Schwarzkopf IGORA ROYAL CSV seed package (batch11)",
            f"Seed product_line={seed_shade['product_line']!r}",
            f"Seed sub_range={seed_shade.get('sub_range')!r}",
        ]
        normalized.append(record)

    tone_ref, tone_norm = build_tone_maps(normalized)
    line_tech = build_line_technical_records(
        _technical_rules_from_csv(tech_rows),
        sources_by_key,
        batch_label="batch11",
    )
    recreation = _formula_recreation_rules(recreation_rows)

    artifacts = {
        "normalized_shade_records": {
            "artifact": "normalized_shade_records",
            "batch": 11,
            "count": len(normalized),
            "package_version": "v5_schwarzkopf_igora",
            "normalized_shade_records": normalized,
        },
        "tone_normalization_map": {
            "artifact": "tone_normalization_map",
            "batch": 11,
            "count": len(tone_norm),
            "tone_normalization_map": tone_norm,
        },
        "manufacturer_tone_reference": {
            "artifact": "manufacturer_tone_reference",
            "batch": 11,
            "count": len(tone_ref),
            "manufacturer_tone_reference": tone_ref,
        },
        "line_technical_records": {
            "artifact": "line_technical_records",
            "batch": 11,
            "count": len(line_tech),
            "line_technical_records": line_tech,
        },
        "formula_recreation_rules": {
            "artifact": "formula_recreation_rules",
            "batch": 11,
            "count": len(recreation),
            "formula_recreation_rules": recreation,
        },
        "manifest": {
            "batch": 11,
            "package_version": "v5_schwarzkopf_igora",
            "shade_records": len(normalized),
            "tone_mappings": len(tone_norm),
            "line_technical_records": len(line_tech),
            "formula_recreation_rules": len(recreation),
            "brands": ["Schwarzkopf Professional"],
            "notes": "IGORA ROYAL quick-starter guide enrichment; recreation formulas kept separate from shade inventory.",
        },
    }
    write_batch_artifacts(B11, artifacts, 11)
    with open(os.path.join(B11, "formula_recreation_rules_batch_11.json"), "w", encoding="utf-8") as handle:
        json.dump(artifacts["formula_recreation_rules"], handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps(artifacts["manifest"], indent=2))


if __name__ == "__main__":
    main()
