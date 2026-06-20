#!/usr/bin/env python3
"""Integrate batch10 v4 Wella / Matrix / L'Oréal seed expansion into stage12_package."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B10 = os.path.join(BASE, "batches", "batch10")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

SHADE_EXTRACTED = {
    "L'Oréal Professionnel::Dia Richesse::global",
}

SOURCE_ADDITIONS = [
    {
        "canonical_key": "Wella Professionals::Koleston Perfect::US",
        "brand_name": "Wella Professionals",
        "product_line_name": "Koleston Perfect",
        "source_title": "Wella Koleston Perfect ME+ colour chart",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "wella.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Koleston Perfect ME+ Pure Naturals, Rich Naturals, Deep Browns, Vibrant Reds, Special Blondes, Special Mix.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "processing_times", "lift_rules"],
        "source_priority_tier": 1,
        "notes": [
            "Wella-Professionals-Koleston-Perfect-ME-Colour-Chart.pdf; batch10 seed package."
        ],
    },
    {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "brand_name": "Wella Professionals",
        "product_line_name": "Color Touch",
        "source_title": "Wella Color Touch system (Rob Eaton 2020 eBook)",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "wella.com",
        "publication_or_revision_date": "2020",
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Color Touch Plus, Sunlights, Relights, Special Mix, Instamatic rules and shades.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "processing_times"],
        "source_priority_tier": 1,
        "notes": [
            "Color-Touch-Rob-Eaton-2020-eBook.pdf; batch10 seed package."
        ],
    },
    {
        "canonical_key": "Matrix::SoColor::US",
        "brand_name": "Matrix",
        "product_line_name": "SoColor",
        "source_title": "Matrix 2023 Haircolor Manual",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "matrix.com",
        "publication_or_revision_date": "2023",
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Hair Diversity Matrix, SoColor/Coil Color/Sync/Tonal Control rules and selected shades.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "lift_rules", "underlying_pigment"],
        "source_priority_tier": 1,
        "notes": [
            "856079182-2023-Matrix-Manual-Haircolor.pdf; batch10 seed package."
        ],
    },
    {
        "canonical_key": "L'Oréal Professionnel::Dia Light::US",
        "brand_name": "L'Oréal Professionnel",
        "product_line_name": "Dia Light",
        "source_title": "L'Oréal Professionnel Dia Light / Dia Richesse color chart",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "lorealprofessionnel.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Dia Light and Dia Richesse shade chart, Diactivateur preparation, coverage and refresh rules.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "processing_times"],
        "source_priority_tier": 1,
        "notes": [
            "366028726-Loreal-Professionnel-Dia-Color-Chart.pdf; batch10 seed package."
        ],
    },
]


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def merge_array(existing: list, incoming: list, key_fn, *, upsert: bool = False) -> tuple[int, int]:
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


def update_gap_report(gap_data: dict) -> None:
    gaps = gap_data["gap_report"]
    gap_data["gap_report"] = [
        gap
        for gap in gaps
        if not (
            gap.get("canonical_key") in SHADE_EXTRACTED
            and gap.get("gap_type") == "shade_extraction_not_started"
        )
    ]


def main() -> None:
    b10_norm = load(os.path.join(B10, "normalized_shade_records_batch_10.json"))
    b10_tone = load(os.path.join(B10, "tone_normalization_map_batch_10.json"))
    b10_tone_ref = load(os.path.join(B10, "manufacturer_tone_reference_batch_10.json"))
    b10_line = load(os.path.join(B10, "line_technical_records_batch_10.json"))

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    shades_added, _ = merge_array(
        c["normalized_shade_records"],
        b10_norm["normalized_shade_records"],
        lambda row: f"{row['canonical_key']}#{row['shade_code']}",
    )
    c["batches_included"] = sorted(set(c.get("batches_included", [])) | {10})
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    line_updates = update_line_technical(d["line_technical_records"], b10_line["line_technical_records"])
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    tone_added, _ = merge_array(
        f["tone_normalization_map"],
        b10_tone["tone_normalization_map"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    ref_added, _ = merge_array(
        e["manufacturer_tone_reference"],
        b10_tone_ref["manufacturer_tone_reference"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
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

    gap_data = load(GAPS)
    update_gap_report(gap_data)
    save(GAPS, gap_data)

    i_path = os.path.join(S12, "I_gap_risk_licensing_report.json")
    i_report = load(i_path)
    update_gap_report(i_report)
    save(i_path, i_report)

    manifest_path = os.path.join(S12, "MANIFEST.json")
    manifest = load(manifest_path)
    manifest["generated"] = date.today().isoformat()
    manifest["coverage"]["normalized_shade_records"] = c["count"]
    manifest["coverage"]["tone_mappings"] = f["count"]
    manifest["coverage"]["tone_reference_rows"] = e["count"]
    manifest["coverage"]["line_technical_records"] = d["count"]
    batches = manifest["coverage"].setdefault("batches_completed", [])
    batch_note = (
        "batch10: Wella Koleston Perfect ME+ and Color Touch system, "
        "Matrix 2023 manual supplement, L'Oréal Dia Light/Dia Richesse"
    )
    if batch_note not in batches:
        batches.append(batch_note)
    save(manifest_path, manifest)

    print(
        json.dumps(
            {
                "shades_added": shades_added,
                "shade_total": c["count"],
                "tone_mappings_added": tone_added,
                "tone_ref_added": ref_added,
                "line_technical_updates": line_updates,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
