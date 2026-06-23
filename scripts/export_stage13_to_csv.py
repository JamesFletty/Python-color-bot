#!/usr/bin/env python3
"""Export stage13 formulation rules to v2 seed CSV.

Rules retain JSON ``rule_condition`` / ``rule_action`` payloads (same surface as
v1 production import) rather than a lossy flatten into scalar columns.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from scripts.v2_paths import (
    FORMULATION_RULES_CSV,
    LINE_OVERRIDES_JSON,
    UNIVERSAL_RULES_JSON,
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _rule_row(
    *,
    package_rule_id: str,
    scope_level: str,
    canonical_key: str,
    rule: dict[str, Any],
    is_dormant: bool = False,
) -> dict[str, str]:
    return {
        "package_rule_id": package_rule_id,
        "scope_level": scope_level,
        "canonical_key": canonical_key,
        "rule_name": str(rule.get("rule_name", "")),
        "rule_priority": str(rule.get("rule_priority", 100)),
        "rule_category": str(rule.get("rule_category", "")),
        "evidence_status": str(rule.get("evidence_status", "")),
        "rule_condition_json": json.dumps(rule.get("rule_condition", {}), ensure_ascii=False),
        "rule_action_json": json.dumps(rule.get("rule_action", {}), ensure_ascii=False),
        "is_dormant": "true" if is_dormant else "false",
    }


def export_rules(path: Path) -> int:
    universal = load_json(UNIVERSAL_RULES_JSON)
    overrides = load_json(LINE_OVERRIDES_JSON)

    rows: list[dict[str, str]] = []
    for rule in universal.get("universal_rules", []):
        rows.append(
            _rule_row(
                package_rule_id=str(rule["rule_id"]),
                scope_level="universal",
                canonical_key="",
                rule=rule,
            )
        )

    for group in overrides.get("brand_line_overrides", []):
        canonical_key = str(group.get("canonical_key", ""))
        requires_inventory = bool(group.get("requires_stage12_inventory_addition"))
        for rule in group.get("override_rules", []):
            rows.append(
                _rule_row(
                    package_rule_id=str(rule["rule_id"]),
                    scope_level="line",
                    canonical_key=canonical_key,
                    rule=rule,
                    is_dormant=requires_inventory,
                )
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "package_rule_id",
        "scope_level",
        "canonical_key",
        "rule_name",
        "rule_priority",
        "rule_category",
        "evidence_status",
        "rule_condition_json",
        "rule_action_json",
        "is_dormant",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    count = export_rules(FORMULATION_RULES_CSV)
    print(f"Wrote {count} rules -> {FORMULATION_RULES_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
