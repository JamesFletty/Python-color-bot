#!/usr/bin/env python3
"""Convert normalized seed package (v3 Aveda Full Spectrum expansion) to Stage 12 batch artifacts."""

from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict
from typing import Any

BASE = os.path.join(os.path.dirname(__file__), "..")
B9 = os.path.join(BASE, "batches", "batch09")
SEED_PATH = os.path.join(B9, "seed_package.json")

LINE_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("Aveda", "Full Spectrum Permanent Hair Color"): {
        "canonical_key": "Aveda::Full Spectrum Permanent::US",
        "product_line": "Full Spectrum Permanent",
        "color_type": "permanent",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Core"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Core",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Highlifts"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Highlifts",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Fashion Lights"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Fashion Lights",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Absolutes"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Absolutes",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Specialties"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Specialties",
    },
    ("Redken", "Shades EQ Gloss / Bonder Inside"): {
        "canonical_key": "Redken::Shades EQ Gloss::US",
        "product_line": "Shades EQ Gloss",
        "color_type": "demi",
    },
    ("Redken", "Color Gels Lacquers"): {
        "canonical_key": "Redken::Color Gels Lacquers::US",
        "product_line": "Color Gels Lacquers",
        "color_type": "permanent",
    },
    ("Redken", "Color Fusion Advanced Performance Color Cream"): {
        "canonical_key": "Redken::Color Fusion::US",
        "product_line": "Color Fusion",
        "color_type": "permanent",
    },
    ("Redken", "Cover Fusion Low Ammonia Color Cream"): {
        "canonical_key": "Redken::Cover Fusion::US",
        "product_line": "Cover Fusion",
        "color_type": "permanent",
    },
    ("Redken", "Color Gels Oils"): {
        "canonical_key": "Redken::Color Gels Oils::US",
        "product_line": "Color Gels Oils",
        "color_type": "permanent",
    },
    ("Redken", "Color Gels 10 Minute"): {
        "canonical_key": "Redken::Color Gels 10 Minute::US",
        "product_line": "Color Gels 10 Minute",
        "color_type": "permanent",
    },
    ("Moroccanoil", "Color Rhapsody Permanent / Color Calypso Demi-Permanent"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
    },
    ("Moroccanoil", "Color Rhapsody Ultimates Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "Ultimates",
    },
    ("Moroccanoil", "Color Rhapsody High Lift"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "High Lift",
    },
    ("Moroccanoil", "Color Calypso / Color Rhapsody shared"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
    },
    ("Moroccanoil", "Color Infusion Pure Color Mixer"): {
        "canonical_key": "Moroccanoil Professional::Color Infusion::US",
        "product_line": "Color Infusion",
        "color_type": "additive",
    },
}

TECH_LINE_MAP: dict[tuple[str, str], dict[str, str]] = {
    **LINE_MAP,
    ("Moroccanoil", "Color Calypso Demi-Permanent Gloss"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
        "sub_range": "Gloss",
    },
    ("Moroccanoil", "Color Calypso Demi-Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
        "sub_range": "Cream",
    },
    ("Moroccanoil", "Color Rhapsody High Lift Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "High Lift",
    },
    ("Moroccanoil", "Color Rhapsody Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
    },
    ("Redken", "Color Fusion Extra Lift"): {
        "canonical_key": "Redken::Color Fusion::US",
        "product_line": "Color Fusion",
        "color_type": "permanent",
        "sub_range": "Extra Lift",
    },
}

IGORA_TONE_MAP: dict[str, list[str]] = {
    "0": ["Natural", "Neutral"],
    "00": ["Natural", "Neutral"],
    "1": ["Ash", "Cool"],
    "11": ["Ash", "Pearl"],
    "12": ["Ash", "Pearl"],
    "13": ["Ash", "Pearl"],
    "4": ["Beige", "Warm"],
    "5": ["Mahogany", "Warm"],
    "55": ["Mahogany", "Warm"],
    "57": ["Mahogany", "Warm"],
    "6": ["Red", "Copper"],
    "63": ["Red", "Copper"],
    "65": ["Red", "Copper"],
    "68": ["Red", "Copper"],
    "7": ["Red", "Warm"],
    "77": ["Red", "Warm"],
    "88": ["Red", "Warm"],
    "98": ["Violet", "Cool"],
    "99": ["Violet", "Cool"],
}

AVEDA_TONE_MAP: dict[str, list[str]] = {
    "Natural": ["Natural"],
    "N/N": ["Natural", "Neutral"],
    "V/B": ["Violet", "Blue", "Ash"],
    "B/B": ["Blue", "Ash"],
    "Y/O": ["Gold", "Copper"],
    "O/R": ["Copper", "Red"],
    "B/V": ["Blue", "Violet", "Ash"],
    "B/G": ["Blue", "Green", "Ash"],
    "R/O": ["Red", "Copper"],
    "V/R": ["Violet", "Red"],
    "R/R": ["Red"],
    "R/V": ["Red", "Violet"],
    "Blue": ["Blue"],
    "Green": ["Green"],
    "Yellow": ["Gold"],
    "Orange": ["Copper"],
    "Violet": ["Violet"],
    "Red": ["Red"],
}


def load_seed() -> dict[str, Any]:
    with open(SEED_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def save(path: str, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def clean_level(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def source_lookup(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["source_key"]: row for row in sources}


def source_document_label(source: dict[str, Any] | None) -> str:
    if not source:
        return "normalized seed package v3"
    return (
        f"{source.get('source_label', '')} "
        f"({source.get('document_filename', '')} pp. {source.get('page_start')}-{source.get('page_end')})"
    ).strip()


def infer_igora_tones(shade_code: str, tone_code: str | None) -> list[str]:
    if tone_code and tone_code in IGORA_TONE_MAP:
        return IGORA_TONE_MAP[tone_code]
    match = re.search(r"-(\d+)$", shade_code)
    if match and match.group(1) in IGORA_TONE_MAP:
        return IGORA_TONE_MAP[match.group(1)]
    if shade_code.startswith(("10-", "12-")):
        return ["Gold", "Warm"]
    if shade_code.startswith("L-"):
        return ["Gold", "Warm"]
    if shade_code.startswith("0-"):
        return ["Neutral", "Other"]
    return []


def infer_aveda_tones(shade: dict[str, Any]) -> list[str]:
    tone_code = shade.get("tone_code")
    if tone_code and tone_code in AVEDA_TONE_MAP:
        return AVEDA_TONE_MAP[tone_code]
    category = shade.get("shade_category") or ""
    if category == "pure_pigment":
        return AVEDA_TONE_MAP.get(shade.get("shade_code", ""), ["Other"])
    if category in {"tone_modifier", "pastel_tone_modifier"}:
        code = shade.get("shade_code", "")
        for key, tones in AVEDA_TONE_MAP.items():
            if key in code:
                return tones
    if category == "base_shade":
        return ["Natural"]
    return []


def infer_normalized_tones(shade: dict[str, Any], brand: str) -> list[str]:
    if brand == "Schwarzkopf Professional":
        tones = infer_igora_tones(shade["shade_code"], shade.get("tone_code"))
    elif brand == "Aveda":
        tones = infer_aveda_tones(shade)
    else:
        tones = []
        tone_code = shade.get("tone_code")
        if tone_code:
            tones = AVEDA_TONE_MAP.get(tone_code, [])
    return tones or ["Other"]


def resolve_sub_range(seed_shade: dict[str, Any], line_cfg: dict[str, str]) -> str | None:
    if seed_shade.get("sub_range"):
        return str(seed_shade["sub_range"])
    if line_cfg.get("sub_range"):
        return line_cfg["sub_range"]
    return None


def build_shade_record(
    seed_shade: dict[str, Any],
    line_cfg: dict[str, str],
    sources_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source = sources_by_key.get(seed_shade.get("source_key", ""))
    tone_code = seed_shade.get("tone_code")
    manufacturer_codes = [tone_code] if tone_code else []
    category = seed_shade.get("shade_category")
    notes: list[str] = []
    if category:
        notes.append(f"shade_category={category}")
    if seed_shade.get("confidence") == "parsed_review_required":
        notes.append("parsed_review_required=true")

    return {
        "canonical_key": line_cfg["canonical_key"],
        "brand": seed_shade["brand"],
        "product_line": line_cfg["product_line"],
        "shade_code": seed_shade["shade_code"],
        "shade_name": seed_shade.get("shade_name") or seed_shade.get("display_code"),
        "level": clean_level(seed_shade.get("level")),
        "manufacturer_tone_codes": manufacturer_codes,
        "manufacturer_tone_descriptions": [],
        "normalized_tones": infer_normalized_tones(seed_shade, seed_shade["brand"]),
        "color_type": line_cfg.get("color_type"),
        "gray_coverage_claim": None,
        "lift_levels": None,
        "mixing_ratio": None,
        "developer_options": None,
        "processing_time_minutes": None,
        "special_usage_notes": "; ".join(notes) if notes else None,
        "sub_range": resolve_sub_range(seed_shade, line_cfg),
        "official_swatch_image_exists": None,
        "region_or_market": "US",
        "discontinued_status": "Active per manufacturer PDF extract (batch09 seed package)",
        "source_url": None,
        "source_document": source_document_label(source),
        "source_type": "manufacturer_pdf",
        "source_publication_date": None,
        "source_confidence": "high" if seed_shade.get("confidence") == "confirmed" else "medium",
        "evidence_status": seed_shade.get("evidence_status", "manufacturer_stated"),
        "assumptions": [
            "Converted from normalized_haircolor_seed_package v3 (batch09)",
            f"Seed product_line={seed_shade['product_line']!r}",
        ],
        "data_gaps": (
            ["parsed_review_required per seed package confidence flag"]
            if seed_shade.get("confidence") == "parsed_review_required"
            else []
        ),
    }


def build_tone_maps(
    shades: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    tone_ref: dict[tuple[str, str], dict[str, Any]] = {}
    tone_norm: dict[tuple[str, str], dict[str, Any]] = {}

    for shade in shades:
        canonical_key = shade["canonical_key"]
        for code in shade.get("manufacturer_tone_codes") or []:
            if not code:
                continue
            ref_key = (canonical_key, code)
            if ref_key not in tone_ref:
                tone_ref[ref_key] = {
                    "canonical_key": canonical_key,
                    "brand": shade["brand"],
                    "product_line": shade["product_line"],
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "source_document": shade.get("source_document"),
                    "evidence_status": shade.get("evidence_status"),
                }
            norm_key = (canonical_key, code)
            if norm_key not in tone_norm:
                tone_norm[norm_key] = {
                    "canonical_key": canonical_key,
                    "brand": shade["brand"],
                    "product_line": shade["product_line"],
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "normalized_tones": shade.get("normalized_tones") or ["Other"],
                    "mapping_rationale": "Inferred from seed package tone_code / shade_category",
                    "mapping_confidence": shade.get("source_confidence", "medium"),
                    "ambiguity_flag": False,
                    "notes": [],
                }
    return list(tone_ref.values()), list(tone_norm.values())


def _append_rule_field(record: dict[str, Any], field: str, label: str, payload: Any) -> None:
    if payload is None:
        return
    existing = record.get(field) or []
    if not isinstance(existing, list):
        existing = [existing]
    existing.append(f"{label}: {json.dumps(payload, ensure_ascii=False)}")
    record[field] = existing


def build_line_technical_records(
    technical_rules: list[dict[str, Any]],
    sources_by_key: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(dict)

    for rule in technical_rules:
        line_key = (rule["brand"], rule["product_line"])
        line_cfg = TECH_LINE_MAP.get(line_key)
        if not line_cfg:
            continue
        canonical_key = line_cfg["canonical_key"]
        record = grouped[canonical_key]
        record.setdefault("canonical_key", canonical_key)
        record.setdefault("brand", rule["brand"] if rule["brand"] != "Moroccanoil" else "Moroccanoil Professional")
        record.setdefault("product_line", line_cfg["product_line"])
        record.setdefault("color_type", line_cfg.get("color_type", "permanent"))
        source = sources_by_key.get(rule.get("source_key", ""))
        record.setdefault("source_document", source_document_label(source))
        record.setdefault("source_type", "manufacturer_pdf")
        record.setdefault("source_confidence", "high")
        record.setdefault("evidence_status", "manufacturer_stated")
        record.setdefault("assumptions", ["Aggregated from normalized seed package technical_rules (batch09)"])
        record.setdefault("data_gaps", [])

        category = rule.get("rule_category", "")
        name = rule.get("rule_name", "")
        action = rule.get("rule_action")
        condition = rule.get("rule_condition")

        if category in {"processing", "application"}:
            _append_rule_field(record, "default_mixing_ratio", name, action.get("mixing_ratio") if isinstance(action, dict) else action)
            _append_rule_field(record, "developer_options", name, action)
            _append_rule_field(record, "processing_time_ranges", name, action.get("processing_time_min") if isinstance(action, dict) else None)
        elif category == "lift":
            _append_rule_field(record, "lift_rules", name, action)
        elif category in {"gray_coverage", "neutralization", "intermixing", "color_science", "correction"}:
            _append_rule_field(record, "gray_coverage_rules", name, {"condition": condition, "action": action})
        elif category == "formulation":
            _append_rule_field(record, "special_usage_notes", name, {"condition": condition, "action": action})
        else:
            _append_rule_field(record, "special_usage_notes", name, rule)

    return list(grouped.values())


def main() -> None:
    pkg = load_seed()
    sources_by_key = source_lookup(pkg.get("sources", []))
    normalized: list[dict[str, Any]] = []

    for seed_shade in pkg.get("shades", []):
        line_key = (seed_shade["brand"], seed_shade["product_line"])
        line_cfg = LINE_MAP.get(line_key)
        if not line_cfg:
            raise KeyError(f"Unmapped seed shade line: {line_key}")
        normalized.append(build_shade_record(seed_shade, line_cfg, sources_by_key))

    tone_ref, tone_norm = build_tone_maps(normalized)
    line_tech = build_line_technical_records(pkg.get("technical_rules", []), sources_by_key)

    save(
        os.path.join(B9, "normalized_shade_records_batch_9.json"),
        {
            "artifact": "normalized_shade_records",
            "batch": 9,
            "count": len(normalized),
            "package_version": pkg.get("metadata", {}).get("package_version"),
            "normalized_shade_records": normalized,
        },
    )
    save(
        os.path.join(B9, "tone_normalization_map_batch_9.json"),
        {
            "artifact": "tone_normalization_map",
            "batch": 9,
            "count": len(tone_norm),
            "tone_normalization_map": tone_norm,
        },
    )
    save(
        os.path.join(B9, "manufacturer_tone_reference_batch_9.json"),
        {
            "artifact": "manufacturer_tone_reference",
            "batch": 9,
            "count": len(tone_ref),
            "manufacturer_tone_reference": tone_ref,
        },
    )
    save(
        os.path.join(B9, "line_technical_records_batch_9.json"),
        {
            "artifact": "line_technical_records",
            "batch": 9,
            "count": len(line_tech),
            "line_technical_records": line_tech,
        },
    )

    manifest = {
        "batch": 9,
        "package_version": pkg.get("metadata", {}).get("package_version"),
        "revision": pkg.get("metadata", {}).get("revision"),
        "shade_records": len(normalized),
        "tone_mappings": len(tone_norm),
        "line_technical_records": len(line_tech),
        "brands": sorted({s["brand"] for s in normalized}),
        "notes": pkg.get("metadata", {}).get("notes"),
    }
    save(os.path.join(B9, "batch_9_manifest.json"), manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
