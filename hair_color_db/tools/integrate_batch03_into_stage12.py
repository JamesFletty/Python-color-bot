#!/usr/bin/env python3
"""Integrate Batch 3 artifacts into stage12_package and update gap reports."""

import json
import os
from copy import deepcopy
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B3 = os.path.join(BASE, "batches", "batch03")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

PRAVANA_EXTRACTED = {
    "Pravana::ChromaSilk Creme Color::US",
    "Pravana::ChromaSilk VIVIDS::US",
    "Pravana::ChromaSilk Express Tones::US",
}

GOLDWELL_LINE_TECH = {
    "Goldwell::Topchic::US": "Topchic",
    "Goldwell::Colorance::US": "Colorance (incl. Cover Plus, Gloss Tones)",
}

JOICO_BATCH3_BLOCKER = (
    "Status: deferred from Batch 3. joico.com returns HTTP 403 (Cloudflare) from automated fetch; "
    "no official PDF mirror found on CosmoProf/SalonCentric."
)
JOICO_BATCH3_ACTION = (
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
        if ck in PRAVANA_EXTRACTED and g["gap_type"] == "shade_extraction_not_started":
            removed += 1
            continue
        if ck in GOLDWELL_LINE_TECH and g["gap_type"] == "shade_extraction_not_started":
            g = deepcopy(g)
            g["gap_type"] = "shade_extraction_blocked"
            g["severity"] = "high"
            g["details"] = (
                "Status: line technical extracted in Batch 3; shade-level Stage 4 blocked — "
                "official Color Guide publishes palette JPEGs without extractable shade codes or companion PDF."
            )
            g["recommended_next_action"] = (
                "Locate machine-readable shade chart/PDF or distributor catalog; "
                "OCR/image extraction only as last resort with manual QA."
            )
            updated += 1
        elif g["brand"] == "Joico" and g["gap_type"] == "shade_extraction_not_started":
            g = deepcopy(g)
            g["gap_type"] = "source_access_blocked"
            g["details"] = JOICO_BATCH3_BLOCKER
            g["recommended_next_action"] = JOICO_BATCH3_ACTION
            updated += 1
        new_gaps.append(g)

    # Pravana tone-legend gap from Batch 3 issue log
    new_gaps.append(
        {
            "canonical_key": "Pravana::ChromaSilk Creme Color::US",
            "brand": "Pravana",
            "product_line": "ChromaSilk Crème Color (Permanent)",
            "gap_type": "tone_legend_partially_inferred",
            "severity": "medium",
            "details": (
                "139 shades extracted in Batch 3. Full digit/combo tone legend lives in pro-gated "
                "Product Knowledge Guide PDF; combo-code mappings partially inferred from public product pages."
            ),
            "recommended_next_action": (
                "Retrieve pro-gated Product Knowledge Guide or official mixing-ratio PDF to confirm inferred tone codes."
            ),
        }
    )

    gap_data["gap_report"] = new_gaps
    gap_data["generated"] = str(date.today())
    return removed, updated


def main():
    b3_norm = load(os.path.join(B3, "normalized_shade_records_batch_3.json"))
    b3_line = load(os.path.join(B3, "line_technical_records_batch_3.json"))
    b3_tone_ref = load(os.path.join(B3, "manufacturer_tone_reference_batch_3.json"))
    b3_tone_map = load(os.path.join(B3, "tone_normalization_map_batch_3.json"))

    # C — normalized shades
    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    added_c = merge_array(
        c["normalized_shade_records"],
        b3_norm["normalized_shade_records"],
        lambda r: f"{r['canonical_key']}#{r['shade_code']}",
    )
    batches = set(c.get("batches_included", [1, 2]))
    batches.add(3)
    c["batches_included"] = sorted(batches)
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    # D — line technical
    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    added_d = merge_array(
        d["line_technical_records"],
        b3_line["line_technical_records"],
        lambda r: r["canonical_key"],
    )
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    # E — manufacturer tone reference
    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    added_e = merge_array(
        e["manufacturer_tone_reference"],
        b3_tone_ref["manufacturer_tone_reference"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    # F — tone normalization map
    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    added_f = merge_array(
        f["tone_normalization_map"],
        b3_tone_map["tone_normalization_map"],
        lambda r: f"{r['canonical_key']}#{r['manufacturer_tone_code']}",
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    # MANIFEST
    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = str(date.today())
    manifest["coverage"]["lines_with_shade_extraction"] = 13
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches_done = manifest["coverage"].get("batches_completed", [])
    batch3_entry = (
        "batch03: Pravana (ChromaSilk Crème Color, Express Tones, VIVIDS); "
        "Goldwell (Topchic, Colorance line technical only)"
    )
    if not any("batch03" in b for b in batches_done):
        batches_done.append(batch3_entry)
    manifest["coverage"]["batches_completed"] = batches_done
    manifest["notes"] = [
        "Confirmed vs inferred data separated via evidence_status / mapping_confidence / ambiguity_flag fields throughout.",
        "Raw manufacturer wording preserved in batches/*/ raw_shade_records files; section C is the normalized layer.",
        f"{133 - 13} inventoried lines remain queued for future extraction batches (see section I gap_report).",
    ]
    save(manifest_path, manifest)

    # Gap reports (stage11 + stage12 section I)
    gap_data = load(GAPS)
    removed, updated = update_gap_report(gap_data)
    save(GAPS, gap_data)
    save(os.path.join(S12, "I_gap_risk_licensing_report.json"), gap_data)

    print("Batch 3 integration complete:")
    print(f"  C normalized shades: +{added_c} -> {c['count']}")
    print(f"  D line technical:    +{added_d} -> {d['count']}")
    print(f"  E tone reference:    +{added_e} -> {e['count']}")
    print(f"  F tone map:          +{added_f} -> {f['count']}")
    print(f"  Gap report: removed {removed} Pravana not-started, updated {updated} gap entries")


if __name__ == "__main__":
    main()
