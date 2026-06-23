#!/usr/bin/env python3
"""Export stage12 shade inventory and brand/line metadata to v2 seed CSVs."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from scripts.export_utils import infer_sub_range, parse_level
from scripts.v2_paths import (
    BRANDS_LINES_CSV,
    LINE_INVENTORY_JSON,
    LINE_TECH_JSON,
    SHADES_CSV,
    SHADES_JSON,
)


RATIO_RE = re.compile(r"\b\d+(?:\.\d+)?:\d+(?:\.\d+)?\b")
VOLUME_RE = re.compile(r"\b(\d{1,2})(?:\s*[- ]?\s*(?:vol|volume|v)\b)", re.IGNORECASE)
MINUTES_RE = re.compile(r"\b(\d{1,3})(?:\s*(?:-|–|to)\s*(\d{1,3}))?\s*(?:min|minutes)\b", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _first_ratio(value: Any) -> str:
    for item in _as_list(value):
        match = RATIO_RE.search(item)
        if match:
            return match.group(0)
    lowered = " ".join(_as_list(value)).lower()
    if "no developer" in lowered or "direct application" in lowered:
        return "no developer"
    return ""


def _default_developer_volume(value: Any) -> int | None:
    volumes: list[int] = []
    for item in _as_list(value):
        volumes.extend(int(match.group(1)) for match in VOLUME_RE.finditer(item))
    if not volumes:
        return None
    if 20 in volumes:
        return 20
    if 10 in volumes:
        return 10
    return min(volumes)


def _default_processing_minutes(value: Any) -> int | None:
    minutes: list[int] = []
    for item in _as_list(value):
        for match in MINUTES_RE.finditer(item):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            minutes.append(round((start + end) / 2))
    if not minutes:
        return None
    if 35 in minutes:
        return 35
    if 20 in minutes:
        return 20
    return minutes[0]


def _line_technical_defaults() -> dict[str, dict[str, Any]]:
    payload = load_json(LINE_TECH_JSON)
    records = payload.get("line_technical_records", [])
    defaults: dict[str, dict[str, Any]] = {}
    for record in records:
        ratio = _first_ratio(record.get("default_mixing_ratio"))
        developer_volume = _default_developer_volume(record.get("developer_strengths_if_stated"))
        processing_minutes = _default_processing_minutes(record.get("processing_time_ranges"))
        defaults[record["canonical_key"]] = {
            "mixing_ratio": ratio or None,
            "developer_volume": developer_volume,
            "processing_time_minutes": processing_minutes,
            "raw": {
                "default_mixing_ratio": record.get("default_mixing_ratio"),
                "developer_options": record.get("developer_options"),
                "developer_strengths_if_stated": record.get("developer_strengths_if_stated"),
                "processing_time_ranges": record.get("processing_time_ranges"),
            },
        }
    return defaults


def export_brands_lines(path: Path) -> int:
    payload = load_json(LINE_INVENTORY_JSON)
    lines = payload.get("brand_line_inventory", [])
    technical_defaults = _line_technical_defaults()
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "canonical_key",
        "brand_name",
        "product_line_name",
        "line_category",
        "mixing_ratio_default",
        "developer_default_volume",
        "processing_time_default_minutes",
        "technical_defaults_json",
        "region_or_market",
        "apparent_status",
        "parent_company",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for line in lines:
            tech = technical_defaults.get(line.get("canonical_key", ""), {})
            writer.writerow(
                {
                    "canonical_key": line.get("canonical_key", ""),
                    "brand_name": line.get("brand_name", ""),
                    "product_line_name": line.get("product_line_name", ""),
                    "line_category": line.get("line_category", ""),
                    "mixing_ratio_default": tech.get("mixing_ratio") or "",
                    "developer_default_volume": tech.get("developer_volume") or "",
                    "processing_time_default_minutes": tech.get("processing_time_minutes") or "",
                    "technical_defaults_json": json.dumps(tech, ensure_ascii=False) if tech else "",
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
