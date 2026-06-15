#!/usr/bin/env python3
"""Build Matrix SoColor Cult and Light Master shade records (Stages 4-8).

Shade inventory transcribed from official PDF text extraction:
  - SoColor Cult vivids palette: 2023 Matrix Manual Haircolor p.65-66 (13 shades)
  - Light Master powder lighteners: 2023 Matrix Manual Haircolor p.70-72 (2 SKUs)
"""
from __future__ import annotations

import json
import os
from typing import Any

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "batches", "batch06")

MATRIX_MANUAL_URL = (
    "https://www.matrix.com/-/media/project/loreal/brand-sites/matrix/americas/us_usmx/"
    "pdf-folder/2023-matrix-manual-haircolor.pdf?rev=4560cb3389094fafb65c166cb50ca5a8"
)
MATRIX_MANUAL_DOC = "2023 Matrix Manual Haircolor (official PDF, 82 pages)"

CULT_KEY = "Matrix::SoColor Cult::US"
LIGHT_KEY = "Matrix::Light Master::US"

# Page 65 SoColor Cult palette — 13 mixable shades (manual p.66 confirms count)
CULT_SHADES: list[dict[str, Any]] = [
    {"shade_code": "DUSTY TEAL", "shade_name": "Dusty Teal", "palette_group": "Dusty's", "normalized_tones": ["Green", "Cool"]},
    {"shade_code": "BUBBLEGUM PINK", "shade_name": "Bubblegum Pink", "palette_group": "Pastel's", "normalized_tones": ["Red", "Pearl"]},
    {"shade_code": "LAVENDER MACARON", "shade_name": "Lavender Macaron", "palette_group": "Pastel's", "normalized_tones": ["Violet"]},
    {"shade_code": "DISCO SILVER", "shade_name": "Disco Silver", "palette_group": "Gray's", "normalized_tones": ["Neutral", "Violet", "Cool"], "notes": "violet-based gray"},
    {"shade_code": "BLACK", "shade_name": "Black", "palette_group": "Gray's", "normalized_tones": ["Blue", "Cool"], "notes": "blue-based black"},
    {"shade_code": "CLEAR", "shade_name": "Clear", "palette_group": "Must-Have's", "normalized_tones": []},
    {"shade_code": "RED HOT", "shade_name": "Red Hot", "palette_group": "Must-Have's", "normalized_tones": ["Red"]},
    {"shade_code": "LUCKY DUCK YELLOW", "shade_name": "Lucky Duck Yellow", "palette_group": "Must-Have's", "normalized_tones": ["Gold", "Warm"]},
    {"shade_code": "ADMIRAL NAVY", "shade_name": "Admiral Navy", "palette_group": "Must-Have's", "normalized_tones": ["Blue"]},
    {"shade_code": "RETRO BLUE", "shade_name": "Retro Blue", "palette_group": "Must-Have's", "normalized_tones": ["Blue"]},
    {"shade_code": "FLAMENCO FUCHSIA", "shade_name": "Flamenco Fuchsia", "palette_group": "Must-Have's", "normalized_tones": ["Violet", "Red"]},
    {"shade_code": "CLOVER GREEN", "shade_name": "Clover Green", "palette_group": "Must-Have's", "normalized_tones": ["Green"]},
    {"shade_code": "ROYAL PURPLE", "shade_name": "Royal Purple", "palette_group": "Must-Have's", "normalized_tones": ["Violet"]},
]

# Light Master portfolio — two powder SKUs under one inventoried line (manual pp.70-72)
LIGHT_MASTER_SHADES: list[dict[str, Any]] = [
    {
        "shade_code": "Light Master",
        "shade_name": "Light Master Classic Technique Powder Lightener",
        "sub_range": "Classic",
        "lift_claim": "Up to 8 levels of lift",
        "bonder": False,
    },
    {
        "shade_code": "Light Master Pre-Bonded",
        "shade_name": "Light Master Pre-Bonded Powder Lightener",
        "sub_range": "Pre-Bonded",
        "lift_claim": "Up to 8 levels of lift; 92% less breakage vs leading lightener without bonder (manual claim)",
        "bonder": True,
    },
]


def line_technical_records() -> list[dict[str, Any]]:
    return [
        {
            "canonical_key": CULT_KEY,
            "brand": "Matrix",
            "product_line": "SoColor Cult (Vivids)",
            "color_type": "direct_dye",
            "default_mixing_ratio": "Direct application — no developer required",
            "developer_options": [],
            "developer_strengths_if_stated": ["No developer needed (manual p.64-66)"],
            "processing_time_ranges": ["Up to 30 minutes (manual p.66)"],
            "gray_coverage_rules": ["Not a gray coverage line; direct dye deposit on level 8-10"],
            "lift_rules": ["No lift; semi-permanent direct dye"],
            "tone_family_legend": [],
            "special_usage_notes": [
                "Virgin and pre-lightened hair; starting level 8-10.",
                "Lasts up to 20 washes; acidic formula; vegan.",
                "SoColor Cult is not Pre-Bonded (manual FAQ p.36).",
                "13 mixable shades; palette mixing recommendations on manual p.65.",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per 2023 Matrix manual",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": ["Shade names only on palette chart; no numeric SKU codes in manual."],
        },
        {
            "canonical_key": LIGHT_KEY,
            "brand": "Matrix",
            "product_line": "Light Master (incl. Light Master Pre-Bonded)",
            "color_type": "lightener",
            "default_mixing_ratio": "Classic off-scalp 1:1.5–1:2; Pre-Bonded off-scalp 1:1.5–1:2; on-scalp 1:2 (manual pp.70-71)",
            "developer_options": [
                "Matrix Cream Developer 10 Volume",
                "Matrix Cream Developer 20 Volume",
                "Matrix Cream Developer 30 Volume",
                "Matrix Cream Developer 40 Volume (off-scalp maximum)",
            ],
            "developer_strengths_if_stated": [
                "Off-scalp up to 40 volume; on-scalp up to 30 volume (manual pp.70-71)",
            ],
            "processing_time_ranges": [
                "Up to 50 minutes; do not use heat; do not cover hair or gather in a bun for on-scalp (manual pp.70-71)",
            ],
            "gray_coverage_rules": [],
            "lift_rules": [
                "Light Master classic: up to 8 levels of lift.",
                "Light Master Pre-Bonded: up to 8 levels with citric acid + glycine bonder (manual pp.70-71).",
            ],
            "tone_family_legend": [],
            "special_usage_notes": [
                "Classic technique powder lightener for foil and lightening techniques.",
                "Pre-Bonded variant pre-mixed with bonder; no separate additive required.",
                "On-scalp application permitted per manual in-depth usage notes (p.72 footnote).",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per 2023 Matrix manual",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [
                "High Riser Pre-Bonded documented separately in manual; not part of this canonical line.",
            ],
            "data_gaps": [
                "Powder lighteners have no tone-code palette; inventory recorded as product SKUs.",
            ],
        },
    ]


def build_cult_records(line_tech: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_records: list[dict[str, Any]] = []
    tone_map: list[dict[str, Any]] = []
    tone_reference: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    for shade in CULT_SHADES:
        code = shade["shade_code"]
        raw = {
            "canonical_key": CULT_KEY,
            "brand": "Matrix",
            "product_line": "SoColor Cult (Vivids)",
            "shade_code": code,
            "shade_name": shade["shade_name"],
            "level": None,
            "manufacturer_tone_codes": [code],
            "manufacturer_tone_descriptions": [],
            "color_type": "semi-permanent direct dye",
            "gray_coverage_claim": None,
            "lift_capability": "No lift; deposit on level 8-10",
            "mixing_ratio": "Direct application — no developer",
            "developer_recommendations": [],
            "processing_time_minutes": 30,
            "special_usage_notes": f"SoColor Cult palette group: {shade['palette_group']}.",
            "official_swatch_image_exists": None,
            "region_or_market": "US",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_type": "official_pdf_manual",
            "source_publication_date": "2023",
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [f"palette_group={shade['palette_group']}"],
            "data_gaps": ["No numeric shade code in manual; shade name used as code."],
        }
        if shade.get("notes"):
            raw["special_usage_notes"] += f" {shade['notes']}."
        raw_records.append(raw)

        tone_map.append(
            {
                "canonical_key": CULT_KEY,
                "brand": "Matrix",
                "product_line": "SoColor Cult (Vivids)",
                "manufacturer_tone_code": code,
                "manufacturer_term": shade["shade_name"],
                "normalized_tones": shade["normalized_tones"] or ["Other"],
                "mapping_rationale": f"Named direct-dye vivid on manual p.65 ({shade['palette_group']})",
                "mapping_confidence": "high",
                "ambiguity_flag": False,
                "notes": [shade["notes"]] if shade.get("notes") else [],
            }
        )
        tone_reference.append(
            {
                "canonical_key": CULT_KEY,
                "brand": "Matrix",
                "product_line": "SoColor Cult (Vivids)",
                "manufacturer_tone_code": code,
                "manufacturer_term": shade["shade_name"],
                "manufacturer_definition": f"SoColor Cult vivid shade — {shade['palette_group']}",
                "confidence": "high",
                "notes_on_ambiguity": [],
            }
        )
        normalized.append(
            {
                "canonical_key": CULT_KEY,
                "brand": "Matrix",
                "product_line": "SoColor Cult (Vivids)",
                "shade_code": code,
                "shade_name": shade["shade_name"],
                "level": None,
                "manufacturer_tone_codes": [code],
                "manufacturer_tone_descriptions": [],
                "normalized_tones": shade["normalized_tones"] or ["Other"],
                "color_type": "semi-permanent direct dye",
                "gray_coverage_claim": None,
                "lift_levels": raw["lift_capability"],
                "mixing_ratio": line_tech.get("default_mixing_ratio"),
                "developer_options": [],
                "processing_time_minutes": 30,
                "special_usage_notes": raw["special_usage_notes"],
                "official_swatch_image_exists": None,
                "region_or_market": "US",
                "discontinued_status": line_tech.get("discontinued_status"),
                "source_url": MATRIX_MANUAL_URL,
                "source_document": MATRIX_MANUAL_DOC,
                "source_type": "official_pdf_manual",
                "source_publication_date": "2023",
                "source_confidence": "high",
                "evidence_status": "confirmed",
                "assumptions": list(raw["assumptions"]),
                "data_gaps": list(raw["data_gaps"]),
            }
        )

    return raw_records, tone_map, tone_reference, normalized


def build_light_records(line_tech: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_records: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    for shade in LIGHT_MASTER_SHADES:
        code = shade["shade_code"]
        raw = {
            "canonical_key": LIGHT_KEY,
            "brand": "Matrix",
            "product_line": "Light Master (incl. Light Master Pre-Bonded)",
            "shade_code": code,
            "shade_name": shade["shade_name"],
            "level": None,
            "manufacturer_tone_codes": [shade["sub_range"]],
            "manufacturer_tone_descriptions": [],
            "color_type": "lightener",
            "gray_coverage_claim": None,
            "lift_capability": shade["lift_claim"],
            "mixing_ratio": line_tech.get("default_mixing_ratio"),
            "developer_recommendations": line_tech.get("developer_options", []),
            "processing_time_minutes": 50,
            "special_usage_notes": f"Matrix powder lightener SKU — {shade['sub_range']} variant.",
            "official_swatch_image_exists": None,
            "region_or_market": "US",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_type": "official_pdf_manual",
            "source_publication_date": "2023",
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [f"sub_range={shade['sub_range']}", f"pre_bonded={shade['bonder']}"],
            "data_gaps": ["Lightener recorded as product SKU; no tone-code palette."],
        }
        raw_records.append(raw)
        normalized.append(
            {
                **raw,
                "normalized_tones": [],
                "lift_levels": shade["lift_claim"],
                "developer_options": line_tech.get("developer_options"),
                "discontinued_status": line_tech.get("discontinued_status"),
                "source_type": raw["source_type"],
                "source_publication_date": raw["source_publication_date"],
            }
        )

    return raw_records, [], [], normalized


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    tech_by_key = {row["canonical_key"]: row for row in line_technical_records()}

    cult_raw, cult_map, cult_tone_ref, cult_norm = build_cult_records(tech_by_key[CULT_KEY])
    light_raw, _, _, light_norm = build_light_records(tech_by_key[LIGHT_KEY])

    raw_records = cult_raw + light_raw
    tone_map = cult_map
    tone_reference = cult_tone_ref
    normalized = cult_norm + light_norm
    line_tech = list(tech_by_key.values())

    def save(name: str, payload: dict[str, Any]) -> None:
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    save(
        "matrix_batch06_raw_shade_records.json",
        {"artifact": "raw_shade_records", "batch": "matrix_batch06", "count": len(raw_records), "raw_shade_records": raw_records},
    )
    save(
        "matrix_batch06_line_technical_records.json",
        {"artifact": "line_technical_records", "batch": "matrix_batch06", "count": len(line_tech), "line_technical_records": line_tech},
    )
    save(
        "matrix_batch06_tone_normalization_map.json",
        {"artifact": "tone_normalization_map", "batch": "matrix_batch06", "count": len(tone_map), "tone_normalization_map": tone_map},
    )
    save(
        "matrix_batch06_manufacturer_tone_reference.json",
        {
            "artifact": "manufacturer_tone_reference",
            "batch": "matrix_batch06",
            "count": len(tone_reference),
            "manufacturer_tone_reference": tone_reference,
        },
    )
    save(
        "normalized_shade_records_batch_6.json",
        {"artifact": "normalized_shade_records", "batch": 6, "count": len(normalized), "normalized_shade_records": normalized},
    )
    save(
        "batch_6_manifest.json",
        {
            "batch": 6,
            "label": "matrix_cult_lightmaster",
            "lines_added": [CULT_KEY, LIGHT_KEY],
            "shade_count": len(normalized),
            "sources": [MATRIX_MANUAL_URL],
        },
    )

    print(f"Matrix batch06 built: {len(normalized)} normalized shades")
    print(f"  SoColor Cult: {len(cult_norm)}")
    print(f"  Light Master: {len(light_norm)}")
    print(f"  Tone mappings: {len(tone_map)}")


if __name__ == "__main__":
    main()
