#!/usr/bin/env python3
"""Integrate Matrix batch06 (SoColor Cult, Light Master) into stage12_package."""

import json
import os
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B6 = os.path.join(BASE, "batches", "batch06")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

SHADE_EXTRACTED = {
    "Matrix::SoColor Cult::US",
    "Matrix::Light Master::US",
}


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

    for g in gaps:
        ck = g["canonical_key"]
        if ck in SHADE_EXTRACTED and g["gap_type"] == "shade_extraction_not_started":
            removed += 1
            continue
        new_gaps.append(g)

    gap_data["gap_report"] = new_gaps
    gap_data["generated"] = str(date.today())
    return removed


def main():
    b6_norm = load(os.path.join(B6, "normalized_shade_records_batch_6.json"))
    b6_tone_ref = load(os.path.join(B6, "matrix_batch06_manufacturer_tone_reference.json"))
    b6_tone_map = load(os.path.join(B6, "matrix_batch06_tone_normalization_map.json"))
    b6_line_tech = load(os.path.join(B6, "matrix_batch06_line_technical_records.json"))

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    added_c = merge_array(
        c["normalized_shade_records"],
        b6_norm["normalized_shade_records"],
        lambda r: f"{r['canonical_key']}#{r['shade_code']}",
    )
    batches = set(c.get("batches_included", [1, 2, 3, 4, 5]))
    batches.add(6)
    c["batches_included"] = sorted(batches)
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    added_d = merge_array(
        d["line_technical_records"],
        b6_line_tech["line_technical_records"],
        lambda r: r["canonical_key"],
    )
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    added_e = merge_array(
        e["manufacturer_tone_reference"],
        b6_tone_ref["manufacturer_tone_reference"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    added_f = merge_array(
        f["tone_normalization_map"],
        b6_tone_map["tone_normalization_map"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = str(date.today())
    manifest["coverage"]["lines_with_shade_extraction"] = (
        manifest["coverage"].get("lines_with_shade_extraction", 22) + 2
    )
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches_done = manifest["coverage"].get("batches_completed", [])
    batch6_entry = "batch06: Matrix (SoColor Cult Vivids, Light Master + Pre-Bonded)"
    if not any("batch06" in b for b in batches_done):
        batches_done.append(batch6_entry)
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

    print("Matrix batch06 integration complete:")
    print(f"  C normalized shades: +{added_c} -> {c['count']}")
    print(f"  D line technical:    +{added_d} -> {d['count']}")
    print(f"  E tone reference:    +{added_e} -> {e['count']}")
    print(f"  F tone map:          +{added_f} -> {f['count']}")
    print(f"  Gap report: removed {removed} extracted gaps")


if __name__ == "__main__":
    main()
