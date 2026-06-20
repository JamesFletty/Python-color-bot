#!/usr/bin/env python3
"""Integrate batch09 normalized seed package (v3 Aveda Full Spectrum expansion) into stage12_package."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B9 = os.path.join(BASE, "batches", "batch09")
S12 = os.path.join(BASE, "stage12_package")
GAPS = os.path.join(BASE, "stage11_gaps", "gap_risk_report.json")

SHADE_EXTRACTED = {
    "Aveda::Full Spectrum Permanent::US",
    "Moroccanoil Professional::Color Rhapsody::US",
    "Moroccanoil Professional::Color Calypso::US",
    "Moroccanoil Professional::Color Infusion::US",
    "Redken::Color Fusion::US",
    "Redken::Cover Fusion::US",
    "Redken::Color Gels Oils::US",
    "Redken::Color Gels 10 Minute::US",
}

INVENTORY_ADDITIONS = [
    {
        "canonical_key": "Redken::Cover Fusion::US",
        "brand_name": "Redken",
        "parent_company": "L'Oréal (Professional Products Division)",
        "product_line_name": "Cover Fusion",
        "line_category": "permanent",
        "apparent_status": "active",
        "region_or_market": "US",
        "official_brand_url": "https://www.redken.com/professional/haircolor",
        "official_line_url": "https://www.redkenpro.com/",
        "notes": [
            "Low-ammonia permanent cream color; shade chart and mixing rules from 1034804579-2025-Product-Guide-Avec-Compression.pdf (batch09 seed package)."
        ],
    },
    {
        "canonical_key": "Redken::Color Gels Oils::US",
        "brand_name": "Redken",
        "parent_company": "L'Oréal (Professional Products Division)",
        "product_line_name": "Color Gels Oils",
        "line_category": "permanent",
        "apparent_status": "active",
        "region_or_market": "US",
        "official_brand_url": "https://www.redken.com/professional/haircolor",
        "official_line_url": "https://www.redkenpro.com/",
        "notes": [
            "Permanent oil-based gel color; extracted from Redken 2025 Product Guide (batch09 seed package)."
        ],
    },
    {
        "canonical_key": "Redken::Color Gels 10 Minute::US",
        "brand_name": "Redken",
        "parent_company": "L'Oréal (Professional Products Division)",
        "product_line_name": "Color Gels 10 Minute",
        "line_category": "permanent",
        "apparent_status": "active",
        "region_or_market": "US",
        "official_brand_url": "https://www.redken.com/professional/haircolor",
        "official_line_url": "https://www.redkenpro.com/",
        "notes": [
            "10-minute permanent gel color line; extracted from Redken 2025 Product Guide (batch09 seed package)."
        ],
    },
]

SOURCE_ADDITIONS = [
    {
        "canonical_key": "Aveda::Full Spectrum Permanent::US",
        "brand_name": "Aveda",
        "product_line_name": "Full Spectrum Permanent",
        "source_title": "Aveda Full Spectrum formulation guidelines and customization chart",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "aveda.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Natural/intense series bases, pure tones, pure pigments, pastel tones, customization matrices.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "formulation_matrices"],
        "source_priority_tier": 1,
        "notes": [
            "452808418-Full-Spectrum-Color.pdf pages 1-2; batch09 seed package."
        ],
    },
    {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "brand_name": "Moroccanoil Professional",
        "product_line_name": "Color Rhapsody",
        "source_title": "Moroccanoil Color Manual shade guide and usage guidelines",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "moroccanoilprofessionals.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Color Rhapsody permanent, high lift, and Ultimates shade/technical coverage.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "processing_times"],
        "source_priority_tier": 1,
        "notes": [
            "900375675-Moroccanoil-Color-Manual-Final-1.pdf; batch09 seed package."
        ],
    },
    {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "brand_name": "Schwarzkopf Professional",
        "product_line_name": "IGORA ROYAL",
        "source_title": "IGORA ROYAL quick-starter guide shade chart and technical instructions",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "schwarzkopf-professional.com",
        "publication_or_revision_date": None,
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Supplemental IGORA ROYAL subline shade chart and mixing/processing rules.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "lift_rules", "gray_coverage"],
        "source_priority_tier": 1,
        "notes": [
            "445122692-schwarzkopf-quick-starter-guide.pdf; batch09 seed package supplement."
        ],
    },
    {
        "canonical_key": "Redken::Color Fusion::US",
        "brand_name": "Redken",
        "product_line_name": "Color Fusion",
        "source_title": "Redken 2025 Product Guide shade and mixing charts",
        "source_type": "manufacturer_pdf",
        "source_url": None,
        "publisher_domain": "redkenpro.com",
        "publication_or_revision_date": "2025",
        "file_type": "pdf",
        "access_status": "available_uploaded_pdf",
        "region_or_market": "US",
        "coverage_summary": "Color Fusion, Cover Fusion, Color Gels Oils, Color Gels 10 Minute shade and technical coverage.",
        "expected_data_types_present": ["shade_codes", "mixing_rules", "processing_times"],
        "source_priority_tier": 1,
        "notes": [
            "1034804579-2025-Product-Guide-Avec-Compression.pdf; batch09 seed package."
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
    kept: list[dict] = []
    for gap in gaps:
        ck = gap["canonical_key"]
        if ck in SHADE_EXTRACTED and gap.get("gap_type") == "shade_extraction_not_started":
            continue
        kept.append(gap)
    gap_data["gap_report"] = kept


def main() -> None:
    b9_norm = load(os.path.join(B9, "normalized_shade_records_batch_9.json"))
    b9_tone = load(os.path.join(B9, "tone_normalization_map_batch_9.json"))
    b9_tone_ref = load(os.path.join(B9, "manufacturer_tone_reference_batch_9.json"))
    b9_line = load(os.path.join(B9, "line_technical_records_batch_9.json"))

    c_path = os.path.join(S12, "C_normalized_shade_records.json")
    c = load(c_path)
    shades_added, _ = merge_array(
        c["normalized_shade_records"],
        b9_norm["normalized_shade_records"],
        lambda row: f"{row['canonical_key']}#{row['shade_code']}",
    )
    c["batches_included"] = sorted(set(c.get("batches_included", [])) | {9})
    c["count"] = len(c["normalized_shade_records"])
    save(c_path, c)

    d_path = os.path.join(S12, "D_line_technical_records.json")
    d = load(d_path)
    line_updates = update_line_technical(d["line_technical_records"], b9_line["line_technical_records"])
    d["count"] = len(d["line_technical_records"])
    save(d_path, d)

    f_path = os.path.join(S12, "F_tone_normalization_map.json")
    f = load(f_path)
    tone_added, _ = merge_array(
        f["tone_normalization_map"],
        b9_tone["tone_normalization_map"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
    )
    f["count"] = len(f["tone_normalization_map"])
    save(f_path, f)

    e_path = os.path.join(S12, "E_manufacturer_tone_reference.json")
    e = load(e_path)
    ref_added, _ = merge_array(
        e["manufacturer_tone_reference"],
        b9_tone_ref["manufacturer_tone_reference"],
        lambda row: f"{row['canonical_key']}#{row['manufacturer_tone_code']}",
    )
    e["count"] = len(e["manufacturer_tone_reference"])
    save(e_path, e)

    a_path = os.path.join(S12, "A_brand_line_inventory.json")
    a = load(a_path)
    merge_array(
        a["brand_line_inventory"],
        INVENTORY_ADDITIONS,
        lambda row: row["canonical_key"],
    )
    save(a_path, a)

    b_path = os.path.join(S12, "B_source_catalog.json")
    b = load(b_path)
    merge_array(
        b["source_catalog"],
        SOURCE_ADDITIONS,
        lambda row: f"{row.get('canonical_key', row.get('source_id', 'unknown'))}#{row.get('source_title', row.get('source_document', ''))}",
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
        "batch09: Aveda Full Spectrum Permanent (natural/pure-tone system), "
        "Moroccanoil Color Rhapsody/Calypso/Infusion, Redken Color Fusion/Cover Fusion/"
        "Color Gels Oils/10 Minute, Schwarzkopf IGORA ROYAL quick-starter supplement"
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
