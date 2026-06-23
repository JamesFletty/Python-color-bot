#!/usr/bin/env python3
"""Phase 1 audit: validate stage12/stage13 artifacts before v2 CSV export."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.v2_paths import (
    CROSS_LINE_JSON,
    EXPECTED_CROSS_LINE_COUNT,
    EXPECTED_SHADE_COUNT,
    LINE_INVENTORY_JSON,
    LINE_OVERRIDES_JSON,
    SHADES_JSON,
    UNIVERSAL_RULES_JSON,
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def audit_shades(payload: dict[str, Any]) -> dict[str, Any]:
    records = payload.get("normalized_shade_records", [])
    pairs = [(r.get("canonical_key"), r.get("shade_code")) for r in records]
    dupes = [k for k, v in Counter(pairs).items() if v > 1]
    missing_level = sum(1 for r in records if r.get("level") is None)
    missing_tones = sum(
        1 for r in records if not r.get("normalized_tones")
    )
    return {
        "count": len(records),
        "expected": EXPECTED_SHADE_COUNT,
        "count_ok": len(records) == EXPECTED_SHADE_COUNT,
        "duplicate_pairs": len(dupes),
        "duplicate_examples": dupes[:5],
        "missing_level": missing_level,
        "missing_normalized_tones": missing_tones,
    }


def audit_cross_line(payload: dict[str, Any]) -> dict[str, Any]:
    entries = payload.get("conversion_entries", [])
    confidences = Counter(e.get("mapping_confidence") for e in entries)
    brands: Counter[str] = Counter()
    for entry in entries:
        key = entry.get("source_canonical_key", "")
        brand = key.split("::")[0] if key else "unknown"
        brands[brand] += 1
    top_brands = brands.most_common(5)
    return {
        "count": len(entries),
        "expected": EXPECTED_CROSS_LINE_COUNT,
        "count_ok": len(entries) == EXPECTED_CROSS_LINE_COUNT,
        "confidence_distribution": dict(confidences),
        "top_source_brands": top_brands,
    }


def audit_rules(universal: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    uni_rules = universal.get("universal_rules", [])
    line_overrides = overrides.get("brand_line_overrides", [])
    override_rule_count = sum(
        len(group.get("override_rules", [])) for group in line_overrides
    )
    elasticity_in_conditions = 0
    for rule in uni_rules:
        blob = json.dumps(rule.get("rule_condition", {}))
        if "elasticity" in blob.lower():
            elasticity_in_conditions += 1
    for group in line_overrides:
        for rule in group.get("override_rules", []):
            blob = json.dumps(rule.get("rule_condition", {}))
            if "elasticity" in blob.lower():
                elasticity_in_conditions += 1
    return {
        "universal_rules": len(uni_rules),
        "line_override_groups": len(line_overrides),
        "line_override_rules": override_rule_count,
        "total_rules": len(uni_rules) + override_rule_count,
        "elasticity_conditions_found": elasticity_in_conditions,
        "note": (
            "Elasticity is supported in engine context (A_formulation_ontology.json) "
            "but stage13 rule JSON may not yet encode elasticity predicates."
        ),
    }


def audit_line_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    lines = payload.get("brand_line_inventory", [])
    keys = [line.get("canonical_key") for line in lines]
    return {
        "count": len(lines),
        "duplicate_canonical_keys": sum(1 for _, v in Counter(keys).items() if v > 1),
    }


def main() -> int:
    report = {
        "shades": audit_shades(load_json(SHADES_JSON)),
        "line_inventory": audit_line_inventory(load_json(LINE_INVENTORY_JSON)),
        "cross_line": audit_cross_line(load_json(CROSS_LINE_JSON)),
        "rules": audit_rules(
            load_json(UNIVERSAL_RULES_JSON),
            load_json(LINE_OVERRIDES_JSON),
        ),
    }

    print(json.dumps(report, indent=2))

    failures: list[str] = []
    if not report["shades"]["count_ok"]:
        failures.append(
            f"shade count {report['shades']['count']} != expected {EXPECTED_SHADE_COUNT}"
        )
    if not report["cross_line"]["count_ok"]:
        failures.append(
            f"cross-line count {report['cross_line']['count']} != expected "
            f"{EXPECTED_CROSS_LINE_COUNT}"
        )

    if failures:
        print("\nAUDIT WARNINGS:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("\nAudit passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
