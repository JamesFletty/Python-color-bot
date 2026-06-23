"""Helpers for Stage 12 CSV export scripts."""

from __future__ import annotations

from typing import Any


def parse_level(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def infer_sub_range(record: dict[str, Any]) -> str:
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
