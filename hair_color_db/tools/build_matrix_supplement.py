#!/usr/bin/env python3
"""Build Matrix Coil Color, Tonal Control, and Super Sync shade records (Stages 4-8).

Shade codes transcribed from official PDF text extraction:
  - Coil Color + Tonal Control: 2023 Matrix Manual Haircolor (82 pp.)
  - Super Sync: Super Sync shade chart PDF (June 2026 launch chart)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "batches", "batch05")

MATRIX_MANUAL_URL = (
    "https://www.matrix.com/-/media/project/loreal/brand-sites/matrix/americas/us_usmx/"
    "pdf-folder/2023-matrix-manual-haircolor.pdf?rev=4560cb3389094fafb65c166cb50ca5a8"
)
MATRIX_MANUAL_DOC = "2023 Matrix Manual Haircolor (official PDF, 82 pages)"
SUPER_SYNC_URL = (
    "https://www.matrix.com/-/media/project/loreal/brand-sites/matrix/americas/us_usmx/"
    "shade-chart-pdfs/super-sync-shade-chart-85x11.pdf?rev=e9af1a88840b4145ad5d4a624d441151"
)
SUPER_SYNC_DOC = "Matrix Super Sync Pre-Bonded shade chart (official PDF, 85x11)"

COIL_KEY = "Matrix::Coil Color::US"
TONAL_KEY = "Matrix::Tonal Control::US"
SYNC_KEY = "Matrix::Super Sync::US"

# Page 39 Coil Color palette (manual states 16 shades; 17 codes transcribed — logged in QA)
COIL_SHADES = [
    "5R", "6A", "6RV", "6RR", "6CC", "6W", "6N",
    "4VV", "4RV", "4W", "4N",
    "8W", "8N", "8GC", "8CG",
    "5M", "7M",
]

# Page 45 Tonal Control acidic gel toner palette (17 shades per manual p.63)
TONAL_SHADES = [
    "9AA", "7NA", "4AA", "9V", "6A", "11PV", "8VG", "4J", "5NJ",
    "9NGA", "5NGA", "6NGA", "5NW", "10PR", "7GM", "9RG", "Totally Transparent",
]

# Super Sync shade chart PDF — all codes visible on chart grid
SUPER_SYNC_SHADES = [
    "1A", "4A", "6A", "6T", "8A", "10A", "7CC+", "10G", "7RR+", "4BR", "8G", "9GV",
    "8BC", "8CG", "6RB", "6RC+", "6G", "6RV+", "4RV+", "6BR", "6BC", "6CG", "5VV",
    "11A", "SP-A", "6P", "8P", "10P", "11P", "SP-P", "8V", "10V", "11V", "SP-V",
    "CLEAR", "HD-RR", "HD-RV", "RED", "BLUE", "8GV", "10NV", "10N", "SP-N",
    "10MM", "9MM", "9NA", "7NA", "8N", "2N", "10NNG", "8NNG", "6NNG", "4NNG", "6N",
    "8WN", "6WN", "5WN", "3N", "8NN", "6NN", "4NN", "7NN", "10NN", "5NN", "3NN", "5N",
    "10M", "8M", "6M", "5M", "SP-M", "4N", "7N", "9N", "6NNA", "10NR",
    "11VG", "8VG", "8AG", "10AG", "SP-AG", "11GV",
]

TAXONOMY = {
    "Natural", "Neutral", "Ash", "Blue", "Green", "Violet", "Pearl", "Gold", "Beige",
    "Copper", "Red", "Mahogany", "Mocha", "Brown", "Warm", "Cool", "Other",
}

MATRIX_LETTERS = {
    "N": ("confirmed", "Neutral", ["Neutral"], "digit legend '.0 Neutral'"),
    "A": ("confirmed", "Ash", ["Ash"], "digit legend '.1 Ash'"),
    "V": ("confirmed", "Violet", ["Violet"], "digit legend '.2 Violet'"),
    "G": ("confirmed", "Gold", ["Gold"], "digit legend '.3 Gold'"),
    "C": ("confirmed", "Copper", ["Copper"], "digit legend '.4 Copper'"),
    "R": ("confirmed", "Red", ["Red"], "digit legend '.6 Red'"),
    "J": ("inferred", "Jade", ["Green"], "digit legend '.7 Jade'"),
    "M": ("inferred", "Mocha", ["Mocha"], "ambiguous vs Mahogany"),
    "P": ("inferred", "Pearl", ["Pearl"], "digit legend '.9 Pearl'"),
    "W": ("inferred", "Warm", ["Warm"], "WN/W family convention"),
    "B": ("inferred", "Brown", ["Brown"], "BR/BC family convention"),
    "T": ("inferred", "Titanium/Ash", ["Ash", "Cool"], "6T on Super Sync chart"),
}
MATRIX_SPECIAL = {
    "CLEAR": ("confirmed", "Clear", [], "non-pigmented clear"),
    "RED": ("confirmed", "Red booster", ["Red"], "printed word RED"),
    "BLUE": ("confirmed", "Blue booster", ["Blue"], "printed word BLUE"),
    "HD-RR": ("confirmed", "HD Red Reflect", ["Red"], "HD series pure reflect"),
    "HD-RV": ("confirmed", "HD Red Violet", ["Red", "Violet"], "HD series pure reflect"),
    "Totally Transparent": ("confirmed", "Totally Transparent", [], "clear acidic toner"),
}


def decode_matrix(code: str) -> tuple[str, str, list[str], str] | None:
    """Decode a Matrix tone token to (status, term, tones, rationale)."""
    if code in MATRIX_SPECIAL:
        st, term, tones, why = MATRIX_SPECIAL[code]
        return st, term, tones, why
    body = code.rstrip("+")
    plus = code.endswith("+")
    if body.startswith("SP-"):
        letter = body[3:]
        sub = decode_matrix(letter) if letter else None
        if sub is None:
            return "inferred", f"Sheer Pastel {letter}", [], "SP sheer pastel series"
        st, term, tones, why = sub
        return "inferred", f"Sheer Pastel {term}", tones, f"SP series + {why}"
    letters = re.findall(r"[A-Z]+", body)
    if not letters or not all(letter in MATRIX_LETTERS for letter in letters):
        return None
    statuses, terms, tones, whys = [], [], [], []
    for letter in letters:
        st, term, tone_list, why = MATRIX_LETTERS[letter]
        statuses.append(st)
        terms.append(term)
        whys.append(why)
        for tone in tone_list:
            if tone not in tones:
                tones.append(tone)
    status = "confirmed" if all(item == "confirmed" for item in statuses) else "inferred"
    label = "/".join(terms) + ("+" if plus else "")
    return status, label, tones, "; ".join(whys)


def parse_level_and_tones(shade_code: str) -> tuple[int | None, list[str]]:
    """Split a Matrix shade code into level prefix and tone token list."""
    if shade_code in MATRIX_SPECIAL:
        return None, [shade_code]
    match = re.match(r"^(\d{1,2})(.+)$", shade_code)
    if not match:
        return None, [shade_code]
    level = int(match.group(1))
    tone_body = match.group(2)
    if tone_body.startswith("SP-"):
        return level, [tone_body]
    tokens = re.findall(r"[A-Z]+\+?", tone_body) or [tone_body]
    return level, tokens


def line_technical_records() -> list[dict[str, Any]]:
    return [
        {
            "canonical_key": COIL_KEY,
            "brand": "Matrix",
            "product_line": "Coil Color",
            "color_type": "permanent",
            "default_mixing_ratio": "1:1 (Coil Color + Coil Color Developer)",
            "developer_options": ["Coil Color Developer 20 Volume", "Coil Color Developer 30 Volume"],
            "developer_strengths_if_stated": ["20 + 30 volume, 1:1 mixing ratio (manual p.39)"],
            "processing_time_ranges": ["35 minutes room temperature (manual p.39)"],
            "gray_coverage_rules": ["Gray ratio tables in Coil Color Technique Guide (Stage 13 reference)"],
            "lift_rules": ["Ammonia-free permanent; visible reflect on dark bases; not positioned as high-lift line"],
            "tone_family_legend": [],
            "special_usage_notes": [
                "Apply to clean dry hair; rinse with Total Results A Curl Can Dream.",
                "On overly porous hair, mist Instacure on mids+ends before first application only.",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per 2023 Matrix manual",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": ["Coil Color gray ratio table lives in separate technique guide PDF."],
        },
        {
            "canonical_key": TONAL_KEY,
            "brand": "Matrix",
            "product_line": "Tonal Control Pre-Bonded",
            "color_type": "demi_acidic",
            "default_mixing_ratio": "1:1 (Tonal Control + 10 Volume (3%) Matrix Cream Developer)",
            "developer_options": ["10 Volume (3%) Matrix Cream Developer"],
            "developer_strengths_if_stated": ["10 Vol only; no lift (manual p.44-45)"],
            "processing_time_ranges": ["20 minutes room temperature (manual p.44)"],
            "gray_coverage_rules": ["Gray blending on pre-lightened hair; not full coverage line"],
            "lift_rules": ["No base shift; acidic gel toner for post-lightening control"],
            "tone_family_legend": [],
            "special_usage_notes": [
                "Apply to dry or damp towel-dried hair.",
                "Totally Transparent dilutes deposit ~1 level when mixed equally.",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per 2023 Matrix manual",
            "source_url": MATRIX_MANUAL_URL,
            "source_document": MATRIX_MANUAL_DOC,
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": [],
        },
        {
            "canonical_key": SYNC_KEY,
            "brand": "Matrix",
            "product_line": "Super Sync Pre-Bonded",
            "color_type": "demi_alkaline",
            "default_mixing_ratio": "1:1 (Super Sync + 10 Volume (3%) Matrix Cream Developer)",
            "developer_options": ["10 Volume (3%) Matrix Cream Developer"],
            "developer_strengths_if_stated": ["10 Vol; up to 1 level lift (product positioning on chart)"],
            "processing_time_ranges": ["20 minutes room temperature on clean 80%+ dry hair (chart footer)"],
            "gray_coverage_rules": [
                "NN/NNG families up to 75% gray; N and warm neutrals up to 50% per chart callouts",
            ],
            "lift_rules": ["Up to 1 level lift; alkaline demi-permanent"],
            "tone_family_legend": [
                {"code": ".1", "meaning": "Ash"}, {"code": ".3", "meaning": "Gold"},
                {"code": ".6", "meaning": "Red"}, {"code": ".9", "meaning": "Pearl"},
            ],
            "special_usage_notes": [
                "HD shades may only be mixed with Super Sync Clear.",
                "SoBoost mixed 3:1 with Super Sync for intensifying/neutralizing boost.",
            ],
            "region_or_market": "US",
            "discontinued_status": "June 2026 launch per shade chart",
            "source_url": SUPER_SYNC_URL,
            "source_document": SUPER_SYNC_DOC,
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": ["Shade names not printed on chart; codes only."],
        },
    ]


def build_raw_record(
    *,
    canonical_key: str,
    product_line: str,
    shade_code: str,
    color_type: str,
    source_url: str,
    source_document: str,
    collection_notes: str,
    gray_claim: str | None = None,
    lift_claim: str | None = None,
    mixing_ratio: str | None = None,
    developer_options: list[str] | None = None,
) -> dict[str, Any]:
    level, tone_codes = parse_level_and_tones(shade_code)
    return {
        "canonical_key": canonical_key,
        "brand": "Matrix",
        "product_line": product_line,
        "shade_code": shade_code,
        "shade_name": None,
        "level": level,
        "manufacturer_tone_codes": tone_codes,
        "manufacturer_tone_descriptions": [],
        "color_type": color_type,
        "gray_coverage_claim": gray_claim,
        "lift_capability": lift_claim,
        "mixing_ratio": mixing_ratio,
        "developer_recommendations": developer_options or [],
        "processing_time_minutes": None,
        "special_usage_notes": collection_notes,
        "official_swatch_image_exists": None,
        "region_or_market": "US",
        "source_url": source_url,
        "source_document": source_document,
        "source_type": "official_pdf_manual",
        "source_publication_date": "2023" if "2023" in source_document else None,
        "source_confidence": "high",
        "evidence_status": "confirmed",
        "assumptions": [],
        "data_gaps": [
            "Shade name not printed per shade in source PDF (palette charts show codes only).",
        ],
    }


def build_records_for_line(
    *,
    canonical_key: str,
    product_line: str,
    shade_codes: list[str],
    color_type: str,
    source_url: str,
    source_document: str,
    line_tech: dict[str, Any],
    collection_notes: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_records = []
    tone_map: dict[tuple[str, str], dict[str, Any]] = {}
    tone_reference = []

    for shade_code in shade_codes:
        raw = build_raw_record(
            canonical_key=canonical_key,
            product_line=product_line,
            shade_code=shade_code,
            color_type=color_type,
            source_url=source_url,
            source_document=source_document,
            collection_notes=collection_notes,
            gray_claim=None,
            lift_claim=line_tech.get("lift_rules", [None])[0] if line_tech.get("lift_rules") else None,
            mixing_ratio=line_tech.get("default_mixing_ratio"),
            developer_options=line_tech.get("developer_options"),
        )
        raw_records.append(raw)

        for code in raw["manufacturer_tone_codes"]:
            key = (canonical_key, code)
            if key in tone_map:
                continue
            decoded = decode_matrix(code)
            if decoded is None:
                tone_reference.append(
                    {
                        "canonical_key": canonical_key,
                        "brand": "Matrix",
                        "product_line": product_line,
                        "manufacturer_tone_code": code,
                        "manufacturer_term": None,
                        "manufacturer_definition": None,
                        "confidence": "unresolved",
                        "notes_on_ambiguity": [f"Could not decode tone token {code!r} from printed legend"],
                    }
                )
                continue
            status, term, tones, why = decoded
            tone_reference.append(
                {
                    "canonical_key": canonical_key,
                    "brand": "Matrix",
                    "product_line": product_line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": term,
                    "manufacturer_definition": why,
                    "confidence": "high" if status == "confirmed" else "medium",
                    "notes_on_ambiguity": [] if status == "confirmed" else [why],
                }
            )
            tone_map[key] = {
                "canonical_key": canonical_key,
                "brand": "Matrix",
                "product_line": product_line,
                "manufacturer_tone_code": code,
                "manufacturer_term": term,
                "normalized_tones": tones,
                "mapping_rationale": why,
                "mapping_confidence": "high" if status == "confirmed" else "medium",
                "ambiguity_flag": status != "confirmed",
                "notes": [],
            }

    normalized = []
    for raw in raw_records:
        tones: list[str] = []
        gaps = list(raw.get("data_gaps") or [])
        assumptions = list(raw.get("assumptions") or [])
        for code in raw["manufacturer_tone_codes"]:
            mapping = tone_map.get((canonical_key, code))
            if mapping:
                for tone in mapping["normalized_tones"]:
                    if tone not in tones:
                        tones.append(tone)
            else:
                gaps.append(f"Tone code {code} unresolved")
        assumptions.append("mixing_ratio inherited from line-level default (supplement line record)")
        assumptions.append("developer_options inherited from line-level record (supplement)")
        normalized.append(
            {
                "canonical_key": canonical_key,
                "brand": "Matrix",
                "product_line": product_line,
                "shade_code": raw["shade_code"],
                "shade_name": raw["shade_name"],
                "level": raw["level"],
                "manufacturer_tone_codes": raw["manufacturer_tone_codes"],
                "manufacturer_tone_descriptions": raw["manufacturer_tone_descriptions"],
                "normalized_tones": tones,
                "color_type": color_type,
                "gray_coverage_claim": raw.get("gray_coverage_claim"),
                "lift_levels": raw.get("lift_capability"),
                "mixing_ratio": line_tech.get("default_mixing_ratio"),
                "developer_options": line_tech.get("developer_options"),
                "processing_time_minutes": None,
                "special_usage_notes": raw.get("special_usage_notes"),
                "official_swatch_image_exists": None,
                "region_or_market": "US",
                "discontinued_status": line_tech.get("discontinued_status"),
                "source_url": raw["source_url"],
                "source_document": raw["source_document"],
                "source_type": raw["source_type"],
                "source_publication_date": raw.get("source_publication_date"),
                "source_confidence": raw["source_confidence"],
                "evidence_status": raw["evidence_status"],
                "assumptions": assumptions,
                "data_gaps": gaps,
            }
        )

    return raw_records, list(tone_map.values()), tone_reference, normalized


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    tech_by_key = {row["canonical_key"]: row for row in line_technical_records()}

    coil_raw, coil_map, coil_tone_ref, coil_norm = build_records_for_line(
        canonical_key=COIL_KEY,
        product_line="Coil Color",
        shade_codes=COIL_SHADES,
        color_type="permanent",
        source_url=MATRIX_MANUAL_URL,
        source_document=MATRIX_MANUAL_DOC,
        line_tech=tech_by_key[COIL_KEY],
        collection_notes="Coil Color palette page (manual p.39); ammonia-free permanent for curls.",
    )
    tonal_raw, tonal_map, tonal_tone_ref, tonal_norm = build_records_for_line(
        canonical_key=TONAL_KEY,
        product_line="Tonal Control Pre-Bonded",
        shade_codes=TONAL_SHADES,
        color_type="demi_acidic",
        source_url=MATRIX_MANUAL_URL,
        source_document=MATRIX_MANUAL_DOC,
        line_tech=tech_by_key[TONAL_KEY],
        collection_notes="Tonal Control acidic gel toner palette (manual p.45).",
    )
    sync_raw, sync_map, sync_tone_ref, sync_norm = build_records_for_line(
        canonical_key=SYNC_KEY,
        product_line="Super Sync Pre-Bonded",
        shade_codes=SUPER_SYNC_SHADES,
        color_type="demi_alkaline",
        source_url=SUPER_SYNC_URL,
        source_document=SUPER_SYNC_DOC,
        line_tech=tech_by_key[SYNC_KEY],
        collection_notes="Super Sync Pre-Bonded shade chart grid.",
    )

    raw_records = coil_raw + tonal_raw + sync_raw
    tone_map = coil_map + tonal_map + sync_map
    tone_reference = coil_tone_ref + tonal_tone_ref + sync_tone_ref
    normalized = coil_norm + tonal_norm + sync_norm
    line_tech = list(tech_by_key.values())

    save = lambda name, payload: open(os.path.join(OUT, name), "w", encoding="utf-8").write(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    )

    save(
        "matrix_supplement_raw_shade_records.json",
        {"artifact": "raw_shade_records", "batch": "matrix_supplement", "count": len(raw_records), "raw_shade_records": raw_records},
    )
    save(
        "matrix_supplement_line_technical_records.json",
        {"artifact": "line_technical_records", "batch": "matrix_supplement", "count": len(line_tech), "line_technical_records": line_tech},
    )
    save(
        "matrix_supplement_tone_normalization_map.json",
        {"artifact": "tone_normalization_map", "batch": "matrix_supplement", "count": len(tone_map), "tone_normalization_map": tone_map},
    )
    save(
        "matrix_supplement_manufacturer_tone_reference.json",
        {
            "artifact": "manufacturer_tone_reference",
            "batch": "matrix_supplement",
            "count": len(tone_reference),
            "manufacturer_tone_reference": tone_reference,
        },
    )
    save(
        "normalized_shade_records_batch_5.json",
        {"artifact": "normalized_shade_records", "batch": 5, "count": len(normalized), "normalized_shade_records": normalized},
    )
    save(
        "batch_5_manifest.json",
        {
            "batch": 5,
            "label": "matrix_supplement",
            "lines_added": [COIL_KEY, TONAL_KEY, SYNC_KEY],
            "shade_count": len(normalized),
            "sources": [MATRIX_MANUAL_URL, SUPER_SYNC_URL],
        },
    )

    print(f"Matrix supplement built: {len(normalized)} normalized shades")
    print(f"  Coil Color: {len(coil_norm)}")
    print(f"  Tonal Control: {len(tonal_norm)}")
    print(f"  Super Sync: {len(sync_norm)}")
    print(f"  Tone mappings: {len(tone_map)}")


if __name__ == "__main__":
    main()
