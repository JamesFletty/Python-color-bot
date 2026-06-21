#!/usr/bin/env python3
"""Integrate batch11 v5 Schwarzkopf IGORA ROYAL CSV enrichment into stage12/stage13."""

from __future__ import annotations

import csv
import json
import os
from copy import deepcopy
from datetime import date
from typing import Any

BASE = os.path.join(os.path.dirname(__file__), "..")
B11 = os.path.join(BASE, "batches", "batch11")
S12 = os.path.join(BASE, "stage12_package")
S13 = os.path.join(BASE, "stage13_formulation_rules")

IGORA_CANONICAL = "Schwarzkopf Professional::IGORA ROYAL::US"

SOURCE_ADDITIONS = [
    {
        "canonical_key": IGORA_CANONICAL,
        "brand_name": "Schwarzkopf Professional",
        "product_line_name": "IGORA ROYAL",
        "source_title": "IGORA ROYAL quick-starter guide (shade chart, recreation formulas, technical)",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "schwarzkopf-professional.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Quick-starter assortment pages 4-5, previous-shade recreation cheat sheet page 6, technical pages 7-10.",
        "expected_data_types_present": [
            "shade_codes",
            "mixing_rules",
            "gray_coverage",
            "lift_rules",
            "formula_recreation",
        ],
        "source_priority_tier": 1,
        "notes": [
            "445122692-schwarzkopf-quick-starter-guide(1).pdf; batch11 v5 CSV seed package.",
        ],
    },
]

CATEGORY_MAP = {
    "processing": "application",
    "lift": "lift",
    "gray_coverage": "gray_coverage",
    "neutralization": "neutralization",
    "toning": "deposit",
    "tone": "deposit",
    "developer": "developer",
    "application": "application",
    "correction": "correction",
    "intermixing": "intermixing",
}


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def merge_array(
    existing: list,
    incoming: list,
    key_fn,
    *,
    upsert: bool = False,
) -> tuple[int, int]:
    index = {key_fn(row): idx for idx, row in enumerate(existing)}
    added = 0
    updated = 0
    for row in incoming:
        key = key_fn(row)
        if key in index:
            if upsert:
                existing[index[key]] = row
                updated += 1
            continue
        existing.append(row)
        index[key] = len(existing) - 1
        added += 1
    return added, updated


def update_line_technical(existing: list[dict], incoming: list[dict]) -> int:
    incoming_by_key = {row["canonical_key"]: row for row in incoming}
    updated = 0
    for idx, row in enumerate(existing):
        replacement = incoming_by_key.get(row["canonical_key"])
        if replacement is None:
            continue
        merged = deepcopy(row)
        for field, value in replacement.items():
            if field in {"canonical_key", "brand", "product_line"}:
                continue
            if isinstance(value, list) and isinstance(merged.get(field), list):
                seen = {json.dumps(item, sort_keys=True) for item in merged[field]}
                for item in value:
                    token = json.dumps(item, sort_keys=True)
                    if token not in seen:
                        merged[field].append(item)
                        seen.add(token)
            elif value is not None:
                merged[field] = value
        existing[idx] = merged
        updated += 1
        del incoming_by_key[row["canonical_key"]]
    for row in incoming_by_key.values():
        existing.append(row)
        updated += 1
    return updated


def load_technical_rules_from_csv() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    with open(os.path.join(B11, "normalized_technical_rules.csv"), encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rules.append(
                {
                    "rule_name": row["rule_name"],
                    "rule_category": row["rule_category"],
                    "rule_condition": json.loads(row["rule_condition"]),
                    "rule_action": json.loads(row["rule_action"]),
                }
            )
    return rules


def _stage13_rule_from_technical(rule: dict[str, Any], idx: int) -> dict[str, Any]:
    condition = rule.get("rule_condition") or {}
    all_of = [{"field": f"seed_{k}", "op": "=", "value": v} for k, v in condition.items()]
    if not all_of:
        all_of = [{"field": "canonical_key", "op": "=", "value": IGORA_CANONICAL}]
    return {
        "rule_id": f"SK_IGORA_V5_{idx:03d}",
        "rule_name": rule["rule_name"],
        "rule_priority": 44 + idx,
        "rule_category": CATEGORY_MAP.get(rule.get("rule_category"), "deposit"),
        "evidence_status": "manufacturer_stated",
        "rule_condition": {"all_of": all_of},
        "rule_action": {
            "seed_rule_name": rule["rule_name"],
            "seed_rule_category": rule.get("rule_category"),
            "manufacturer_rule_action": rule.get("rule_action"),
            "warning": f"Apply per IGORA ROYAL quick-starter guide: {rule['rule_name']}",
        },
    }


def _stage13_rule_from_recreation(rule: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "rule_id": f"SK_IGORA_REC_{idx:03d}",
        "rule_name": f"igora_recreate_{rule['previous_shade_code'].replace('/', '_')}",
        "rule_priority": 35 + idx,
        "rule_category": "correction",
        "evidence_status": "manufacturer_stated",
        "rule_condition": {
            "all_of": [
                {
                    "field": "target_shade_code",
                    "op": "=",
                    "value": rule["previous_shade_code"],
                }
            ]
        },
        "rule_action": {
            "migration_recreation_formula": True,
            "mixing_possible": rule.get("mixing_possible", False),
            "ratio": rule.get("ratio"),
            "components": rule.get("components"),
            "developer_grams": rule.get("developer_grams"),
            "recreation_formula_text": rule.get("recreation_formula_text"),
            "warning": (
                "Previous-shade recreation formula from IGORA ROYAL page 6 cheat sheet; "
                "not an active inventory shade."
            ),
        },
    }


def append_stage13_rules(
    technical_rules: list[dict[str, Any]],
    recreation_rules: list[dict[str, Any]],
) -> int:
    d_path = os.path.join(S13, "D_brand_line_overrides.json")
    d = load(d_path)
    group = next(g for g in d["brand_line_overrides"] if g["canonical_key"] == IGORA_CANONICAL)
    existing_names = {r["rule_name"] for r in group["override_rules"]}
    existing_ids = {r["rule_id"] for r in group["override_rules"]}
    added = 0

    for idx, rule in enumerate(technical_rules, start=1):
        if rule["rule_name"] in existing_names:
            continue
        entry = _stage13_rule_from_technical(rule, idx)
        while entry["rule_id"] in existing_ids:
            entry["rule_id"] = f"{entry['rule_id']}_b"
        group["override_rules"].append(entry)
        existing_names.add(entry["rule_name"])
        existing_ids.add(entry["rule_id"])
        added += 1

    for idx, rule in enumerate(recreation_rules, start=1):
        entry = _stage13_rule_from_recreation(rule, idx)
        if entry["rule_name"] in existing_names:
            continue
        while entry["rule_id"] in existing_ids:
            entry["rule_id"] = f"{entry['rule_id']}_b"
        group["override_rules"].append(entry)
        existing_names.add(entry["rule_name"])
        existing_ids.add(entry["rule_id"])
        added += 1

    save(d_path, d)
    manifest = load(os.path.join(S13, "MANIFEST.json"))
    manifest["counts"]["brand_line_overrides"] = len(d["brand_line_overrides"])
    save(os.path.join(S13, "MANIFEST.json"), manifest)
    return added


def main() -> None:
    b11_norm = load(os.path.join(B11, "normalized_shade_records_batch_11.json"))
    b11_tone = load(os.path.join(B11, "tone_normalization_map_batch_11.json"))
    b11_tone_ref = load(os.path.join(B11, "manufacturer_tone_reference_batch_11.json"))
    b11_line = load(os.path.join(B11, "line_technical_records_batch_11.json"))
    b11_recreation = load(os.path.join(B11, "formula_recreation_rules_batch_11.json"))

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    shades_added, shades_updated = merge_array(
        c["normalized_shade_records"],
        b11_norm["normalized_shade_records"],
        lambda row: f"{row['canonical_key']}#{row['shade_code']}",
        upsert=True,
    )
    c["batches_included"] = sorted(set(c.get("batches_included", [])) | {11})
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    line_updates = update_line_technical(d["line_technical_records"], b11_line["line_technical_records"])
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    tone_added, tone_updated = merge_array(
        f["tone_normalization_map"],
        b11_tone["tone_normalization_map"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
        upsert=True,
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    ref_added, ref_updated = merge_array(
        e["manufacturer_tone_reference"],
        b11_tone_ref["manufacturer_tone_reference"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
        upsert=True,
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    b_path = os.path.join(S12, "B_source_catalog.json")
    b = load(b_path)
    merge_array(
        b["source_catalog"],
        SOURCE_ADDITIONS,
        lambda row: f"{row.get('canonical_key', row.get('source_id', 'unknown'))}#{row.get('source_title', '')}",
    )
    save(b_path, b)

    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = date.today().isoformat()
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches = manifest["coverage"].setdefault("batches_completed", [])
    batch_note = (
        "batch11: Schwarzkopf IGORA ROYAL quick-starter enrichment "
        "(sub-range metadata, technical rules, previous-shade recreation formulas)"
    )
    if batch_note not in batches:
        batches.append(batch_note)
    save(manifest_path, manifest)

    stage13_added = append_stage13_rules(
        load_technical_rules_from_csv(),
        b11_recreation["formula_recreation_rules"],
    )

    print(
        json.dumps(
            {
                "shades_added": shades_added,
                "shades_updated": shades_updated,
                "shade_total": c["count"],
                "tone_mappings_added": tone_added,
                "tone_mappings_updated": tone_updated,
                "line_technical_updates": line_updates,
                "stage13_rules_added": stage13_added,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
