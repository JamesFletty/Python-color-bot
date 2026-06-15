#!/usr/bin/env python3
"""Integrate Goldwell batch07 (Topchic, Colorance) into stage12_package."""

import json
import os
from copy import deepcopy
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B7 = os.path.join(BASE, "batches", "batch07")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

SHADE_EXTRACTED = {
    "Goldwell::Topchic::US",
    "Goldwell::Colorance::US",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def merge_array(existing, incoming, key_fn, *, upsert: bool = False):
    index = {key_fn(r): i for i, r in enumerate(existing)}
    added = 0
    updated = 0
    for rec in incoming:
        k = key_fn(rec)
        if k in index:
            if upsert:
                existing[index[k]] = rec
                updated += 1
            continue
        existing.append(rec)
        index[k] = len(existing) - 1
        added += 1
    return added, updated


def update_line_technical(existing: list[dict], incoming: list[dict]) -> int:
    incoming_by_key = {row["canonical_key"]: row for row in incoming}
    updated = 0
    for idx, row in enumerate(existing):
        key = row["canonical_key"]
        if key not in incoming_by_key:
            continue
        merged = deepcopy(incoming_by_key[key])
        merged["source_confidence"] = row.get("source_confidence", merged.get("source_confidence"))
        existing[idx] = merged
        updated += 1
    return updated


def update_gap_report(gap_data):
    gaps = gap_data["gap_report"]
    new_gaps = []
    removed = 0

    for g in gaps:
        ck = g["canonical_key"]
        if ck in SHADE_EXTRACTED and g["gap_type"] in (
            "shade_extraction_not_started",
            "shade_extraction_blocked",
        ):
            removed += 1
            continue
        new_gaps.append(g)

    gap_data["gap_report"] = new_gaps
    gap_data["generated"] = str(date.today())
    return removed


def main():
    b7_norm = load(os.path.join(B7, "normalized_shade_records_batch_7.json"))
    b7_tone_ref = load(os.path.join(B7, "goldwell_batch07_manufacturer_tone_reference.json"))
    b7_tone_map = load(os.path.join(B7, "goldwell_batch07_tone_normalization_map.json"))
    b7_line_tech = load(os.path.join(B7, "goldwell_batch07_line_technical_records.json"))

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    added_c, updated_c = merge_array(
        c["normalized_shade_records"],
        b7_norm["normalized_shade_records"],
        lambda r: f"{r['canonical_key']}#{r['shade_code']}",
        upsert=True,
    )
    batches = set(c.get("batches_included", [1, 2, 3, 4, 5, 6]))
    batches.add(7)
    c["batches_included"] = sorted(batches)
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    updated_d = update_line_technical(d["line_technical_records"], b7_line_tech["line_technical_records"])
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    added_e, updated_e = merge_array(
        e["manufacturer_tone_reference"],
        b7_tone_ref["manufacturer_tone_reference"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
        upsert=True,
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    added_f, updated_f = merge_array(
        f["tone_normalization_map"],
        b7_tone_map["tone_normalization_map"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
        upsert=True,
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = str(date.today())
    manifest["coverage"]["lines_with_shade_extraction"] = (
        manifest["coverage"].get("lines_with_shade_extraction", 24) + 2
    )
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches_done = manifest["coverage"].get("batches_completed", [])
    batch7_entry = "batch07: Goldwell (Topchic permanent, Colorance demi-permanent)"
    if not any("batch07" in b for b in batches_done):
        batches_done.append(batch7_entry)
    manifest["coverage"]["batches_completed"] = batches_done
    remaining = manifest["coverage"]["lines_inventoried"] - manifest["coverage"]["lines_with_shade_extraction"]
    manifest["notes"] = [
        "Confirmed vs inferred data separated via evidence_status / mapping_confidence / ambiguity_flag fields throughout.",
        "Raw manufacturer wording preserved in batches/*/ raw_shade_records files; section C is the normalized layer.",
        f"{remaining} inventoried lines remain queued for future extraction batches (see section I gap_report).",
    ]
    save(manifest_path, manifest)

    gap_data = load(GAPS)
    removed = update_gap_report(gap_data)
    save(GAPS, gap_data)
    save(os.path.join(S12, "I_gap_risk_licensing_report.json"), gap_data)

    print("Goldwell batch07 integration complete:")
    print(f"  C normalized shades: +{added_c} updated {updated_c} -> {c['count']}")
    print(f"  D line technical:    updated {updated_d} existing rows -> {d['count']}")
    print(f"  E tone reference:    +{added_e} updated {updated_e} -> {e['count']}")
    print(f"  F tone map:          +{added_f} updated {updated_f} -> {f['count']}")
    print(f"  Gap report: removed {removed} blocked/not-started gaps")


if __name__ == "__main__":
    main()
