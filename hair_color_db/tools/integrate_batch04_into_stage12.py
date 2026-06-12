#!/usr/bin/env python3
"""Integrate Batch 4 artifacts into stage12_package and update gap reports."""

import json
import os
from copy import deepcopy
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B4 = os.path.join(BASE, "batches", "batch04")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

SHADE_EXTRACTED = {
    "Pravana::ChromaSilk VIVIDS Everlasting::US",
    "Pulp Riot::Semi-Permanent::US",
    "Kenra Professional::Kenra Color Permanent::US",
    "Kenra Professional::Kenra Color Demi-Permanent::US",
    "Kenra Professional::Kenra Color Rapid Toners::US",
    "Kenra Professional::Studio Stylist Express::US",
}

LINE_TECH_ONLY = {
    "Kenra Professional::Kenra Color Creatives::US": (
        "shade_extraction_blocked",
        "Status: line technical extracted in Batch 4; shade-level Stage 4 blocked — "
        "official /color-list?filter=creatives renders shade inventory client-side without public PDF.",
        "Locate machine-readable Creatives shade chart/PDF or authenticated color-list API export.",
    ),
    "Paul Mitchell::The Demi::global": (
        "shade_extraction_blocked",
        "Status: line technical extracted in Batch 4; shade-level Stage 4 blocked — "
        "official paulmitchell.co.th page publishes 65+ swatches as images only.",
        "Locate official The Demi shade chart PDF or distributor catalog with extractable codes.",
    ),
}

JOICO_BATCH4_BLOCKER = (
    "Status: deferred from Batch 4. joico.com and direct PDF URLs return HTTP 403 (Cloudflare); "
    "no official distributor PDF mirror found."
)
JOICO_BATCH4_ACTION = (
    "Retry from residential IP, use manufacturer education portal login, or locate distributor-hosted PDF."
)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def merge_array(existing, incoming, key_fn):
    seen = {key_fn(r) for r in existing}
    added = 0
    for rec in incoming:
        k = key_fn(rec)
        if k not in seen:
            existing.append(rec)
            seen.add(k)
            added += 1
    return added


def update_gap_report(gap_data):
    gaps = gap_data["gap_report"]
    new_gaps = []
    removed = 0
    updated = 0

    for g in gaps:
        ck = g["canonical_key"]
        if ck in SHADE_EXTRACTED and g["gap_type"] == "shade_extraction_not_started":
            removed += 1
            continue
        if ck in LINE_TECH_ONLY and g["gap_type"] == "shade_extraction_not_started":
            g = deepcopy(g)
            g["gap_type"], g["details"], g["recommended_next_action"] = LINE_TECH_ONLY[ck]
            g["severity"] = "high"
            updated += 1
        elif g["brand"] == "Joico" and g["gap_type"] in (
            "shade_extraction_not_started",
            "source_access_blocked",
        ):
            g = deepcopy(g)
            g["gap_type"] = "source_access_blocked"
            g["details"] = JOICO_BATCH4_BLOCKER
            g["recommended_next_action"] = JOICO_BATCH4_ACTION
            updated += 1
        new_gaps.append(g)

    new_gaps.append(
        {
            "canonical_key": "Pulp Riot::Semi-Permanent::US",
            "brand": "Pulp Riot",
            "product_line": "Pulp Riot Semi-Permanent (Paint)",
            "gap_type": "partial_line_coverage",
            "severity": "medium",
            "details": (
                "29 shades extracted in Batch 4 from 6 sub-collections; official line claims 44+ shades — "
                "remaining shades not on crawled collection pages."
            ),
            "recommended_next_action": (
                "Crawl remaining sub-collections or official shade chart when cataloged."
            ),
        }
    )

    gap_data["gap_report"] = new_gaps
    gap_data["generated"] = str(date.today())
    return removed, updated


def main():
    b4_norm = load(os.path.join(B4, "normalized_shade_records_batch_4.json"))
    b4_tone_ref = load(os.path.join(B4, "manufacturer_tone_reference_batch_4.json"))
    b4_tone_map = load(os.path.join(B4, "tone_normalization_map_batch_4.json"))

    line_tech = []
    for fname in (
        "pravana_line_technical_records.json",
        "pulpriot_line_technical_records.json",
        "kenra_line_technical_records.json",
        "paulmitchell_line_technical_records.json",
    ):
        path = os.path.join(B4, fname)
        if os.path.exists(path):
            line_tech += load(path)["line_technical_records"]

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    added_c = merge_array(
        c["normalized_shade_records"],
        b4_norm["normalized_shade_records"],
        lambda r: f"{r['canonical_key']}#{r['shade_code']}",
    )
    batches = set(c.get("batches_included", [1, 2, 3]))
    batches.add(4)
    c["batches_included"] = sorted(batches)
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    added_d = merge_array(
        d["line_technical_records"],
        line_tech,
        lambda r: r["canonical_key"],
    )
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    added_e = merge_array(
        e["manufacturer_tone_reference"],
        b4_tone_ref["manufacturer_tone_reference"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    added_f = merge_array(
        f["tone_normalization_map"],
        b4_tone_map["tone_normalization_map"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = str(date.today())
    manifest["coverage"]["lines_with_shade_extraction"] = (
        manifest["coverage"].get("lines_with_shade_extraction", 13) + 6
    )
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches_done = manifest["coverage"].get("batches_completed", [])
    batch4_entry = (
        "batch04: Pravana (VIVIDS Everlasting), Pulp Riot (Semi-Permanent Paint), "
        "Kenra (Permanent, Demi, Rapid Toners, Studio Stylist Express); "
        "Paul Mitchell (The Demi line tech), Kenra (Creatives line tech)"
    )
    if not any("batch04" in b for b in batches_done):
        batches_done.append(batch4_entry)
    manifest["coverage"]["batches_completed"] = batches_done
    manifest["notes"] = [
        "Confirmed vs inferred data separated via evidence_status / mapping_confidence / ambiguity_flag fields throughout.",
        "Raw manufacturer wording preserved in batches/*/ raw_shade_records files; section C is the normalized layer.",
        f"{133 - manifest['coverage']['lines_with_shade_extraction']} inventoried lines remain queued for future extraction batches (see section I gap_report).",
    ]
    save(manifest_path, manifest)

    gap_data = load(GAPS)
    removed, updated = update_gap_report(gap_data)
    save(GAPS, gap_data)
    save(os.path.join(S12, "I_gap_risk_licensing_report.json"), gap_data)

    print("Batch 4 integration complete:")
    print(f"  C normalized shades: +{added_c} -> {c['count']}")
    print(f"  D line technical:    +{added_d} -> {d['count']}")
    print(f"  E tone reference:    +{added_e} -> {e['count']}")
    print(f"  F tone map:          +{added_f} -> {f['count']}")
    print(f"  Gap report: removed {removed} extracted gaps, updated {updated} entries")


if __name__ == "__main__":
    main()
