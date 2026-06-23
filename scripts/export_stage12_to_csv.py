#!/usr/bin/env python3
"""Export stage12 shade inventory and brand/line metadata to v2 seed CSVs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from scripts.export_utils import infer_sub_range, parse_level
from scripts.v2_paths import (
    BRANDS_LINES_CSV,
    LINE_INVENTORY_JSON,
    SHADES_CSV,
    SHADES_JSON,
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def export_brands_lines(path: Path) -> int:
    payload = load_json(LINE_INVENTORY_JSON)
    lines = payload.get("brand_line_inventory", [])
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "canonical_key",
        "brand_name",
        "product_line_name",
        "line_category",
        "region_or_market",
        "apparent_status",
        "parent_company",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for line in lines:
            writer.writerow(
                {
                    "canonical_key": line.get("canonical_key", ""),
                    "brand_name": line.get("brand_name", ""),
                    "product_line_name": line.get("product_line_name", ""),
                    "line_category": line.get("line_category", ""),
                    "region_or_market": line.get("region_or_market", ""),
                    "apparent_status": line.get("apparent_status", ""),
                    "parent_company": line.get("parent_company", ""),
                }
            )
    return len(lines)


def export_shades(path: Path) -> int:
    payload = load_json(SHADES_JSON)
    records = payload.get("normalized_shade_records", [])
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "canonical_key",
        "brand",
        "product_line",
        "shade_code",
        "shade_name",
        "level",
        "normalized_tones",
        "color_type",
        "sub_range",
        "mixing_ratio",
        "discontinued_status",
        "gray_coverage_claim",
        "metadata_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            metadata = {
                k: record.get(k)
                for k in (
                    "manufacturer_tone_codes",
                    "manufacturer_tone_descriptions",
                    "developer_options",
                    "processing_time_minutes",
                    "special_usage_notes",
                    "source_url",
                    "source_confidence",
                    "evidence_status",
                    "assumptions",
                    "data_gaps",
                )
                if record.get(k) is not None
            }
            tones = record.get("normalized_tones") or []
            writer.writerow(
                {
                    "canonical_key": record.get("canonical_key", ""),
                    "brand": record.get("brand", ""),
                    "product_line": record.get("product_line", ""),
                    "shade_code": record.get("shade_code", ""),
                    "shade_name": record.get("shade_name", ""),
                    "level": parse_level(record.get("level")),
                    "normalized_tones": "|".join(str(t) for t in tones),
                    "color_type": record.get("color_type", ""),
                    "sub_range": infer_sub_range(record),
                    "mixing_ratio": record.get("mixing_ratio", ""),
                    "discontinued_status": record.get("discontinued_status", ""),
                    "gray_coverage_claim": record.get("gray_coverage_claim", ""),
                    "metadata_json": json.dumps(metadata, ensure_ascii=False)
                    if metadata
                    else "",
                }
            )
    return len(records)


def main() -> int:
    line_count = export_brands_lines(BRANDS_LINES_CSV)
    shade_count = export_shades(SHADES_CSV)
    print(f"Wrote {line_count} lines -> {BRANDS_LINES_CSV}")
    print(f"Wrote {shade_count} shades -> {SHADES_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
