"""Build Stage 12 batch artifacts from a normalized seed package JSON file."""

from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict
from typing import Any, Callable

from seed_package_mappings import LINE_MAP, TECH_LINE_MAP

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

GENERIC_TONE_MAP: dict[str, list[str]] = {
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
    "0": ["Natural", "Neutral"],
    "1": ["Ash", "Cool"],
    "3": ["Gold", "Warm"],
    "4": ["Copper", "Red"],
    "5": ["Mahogany", "Warm"],
    "6": ["Red", "Copper"],
    "7": ["Brown", "Warm"],
    "8": ["Mocha", "Warm"],
    "07": ["Natural", "Brown"],
    "17": ["Brown", "Cool"],
    "18": ["Mocha", "Warm"],
    "34": ["Gold", "Copper"],
    "43": ["Beige", "Gold"],
    "53": ["Gold", "Warm"],
    "65": ["Red", "Mahogany"],
    "73": ["Brown", "Gold"],
    "A": ["Ash"],
    "N": ["Natural"],
    "G": ["Gold"],
    "R": ["Red"],
    "V": ["Violet"],
    "C": ["Copper"],
    "M": ["Mahogany"],
    "B": ["Beige"],
    "RV": ["Red", "Violet"],
    "GB": ["Gold", "Beige"],
    "NA": ["Natural", "Ash"],
}


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


def source_document_label(source: dict[str, Any] | None, *, fallback: str) -> str:
    if not source:
        return fallback
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
    if tone_code and tone_code in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[tone_code]
    category = shade.get("shade_category") or ""
    if category == "pure_pigment":
        return GENERIC_TONE_MAP.get(shade.get("shade_code", ""), ["Other"])
    if category in {"tone_modifier", "pastel_tone_modifier"}:
        code = shade.get("shade_code", "")
        for key, tones in GENERIC_TONE_MAP.items():
            if key in code:
                return tones
    if category == "base_shade":
        return ["Natural"]
    return []


def infer_wella_tones(shade: dict[str, Any]) -> list[str]:
    tone_code = shade.get("tone_code")
    if tone_code and tone_code in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[tone_code]
    match = re.search(r"/(\d+)$", shade.get("shade_code", ""))
    if match and match.group(1) in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[match.group(1)]
    suffix = re.sub(r"^\d+/?", "", shade.get("shade_code", ""))
    if suffix in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[suffix]
    return []


def infer_matrix_tones(shade: dict[str, Any]) -> list[str]:
    code = shade.get("shade_code", "")
    suffix = re.sub(r"^\d+", "", code)
    if suffix in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[suffix]
    tone_code = shade.get("tone_code")
    if tone_code and tone_code in GENERIC_TONE_MAP:
        return GENERIC_TONE_MAP[tone_code]
    return []


def infer_normalized_tones(shade: dict[str, Any], brand: str) -> list[str]:
    if brand == "Schwarzkopf Professional":
        tones = infer_igora_tones(shade["shade_code"], shade.get("tone_code"))
    elif brand == "Aveda":
        tones = infer_aveda_tones(shade)
    elif brand == "Wella Professionals":
        tones = infer_wella_tones(shade)
    elif brand == "Matrix":
        tones = infer_matrix_tones(shade)
    else:
        tones = []
        tone_code = shade.get("tone_code")
        if tone_code and tone_code in GENERIC_TONE_MAP:
            tones = GENERIC_TONE_MAP[tone_code]
    return tones or ["Other"]


def resolve_sub_range(seed_shade: dict[str, Any], line_cfg: dict[str, str]) -> str | None:
    if seed_shade.get("sub_range"):
        return str(seed_shade["sub_range"])
    if line_cfg.get("sub_range"):
        return line_cfg["sub_range"]
    return None


def line_key(brand: str, product_line: str | None) -> tuple[str, str | None]:
    return brand, product_line


def build_shade_record(
    seed_shade: dict[str, Any],
    line_cfg: dict[str, str],
    sources_by_key: dict[str, dict[str, Any]],
    *,
    batch_label: str,
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
        "discontinued_status": f"Active per manufacturer PDF extract ({batch_label})",
        "source_url": None,
        "source_document": source_document_label(
            source,
            fallback=f"normalized seed package ({batch_label})",
        ),
        "source_type": "manufacturer_pdf",
        "source_publication_date": None,
        "source_confidence": "high" if seed_shade.get("confidence") == "confirmed" else "medium",
        "evidence_status": seed_shade.get("evidence_status", "manufacturer_stated"),
        "assumptions": [
            f"Converted from normalized_haircolor_seed_package ({batch_label})",
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


def _brand_label(brand: str) -> str:
    if brand == "Moroccanoil":
        return "Moroccanoil Professional"
    return brand


def build_line_technical_records(
    technical_rules: list[dict[str, Any]],
    sources_by_key: dict[str, dict[str, Any]],
    *,
    batch_label: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(dict)

    for rule in technical_rules:
        line_cfg = TECH_LINE_MAP.get(line_key(rule["brand"], rule.get("product_line")))
        if not line_cfg:
            continue
        canonical_key = line_cfg["canonical_key"]
        record = grouped[canonical_key]
        record.setdefault("canonical_key", canonical_key)
        record.setdefault("brand", _brand_label(rule["brand"]))
        record.setdefault("product_line", line_cfg["product_line"])
        record.setdefault("color_type", line_cfg.get("color_type", "permanent"))
        source = sources_by_key.get(rule.get("source_key", ""))
        record.setdefault(
            "source_document",
            source_document_label(source, fallback=f"normalized seed package ({batch_label})"),
        )
        record.setdefault("source_type", "manufacturer_pdf")
        record.setdefault("source_confidence", "high")
        record.setdefault("evidence_status", "manufacturer_stated")
        record.setdefault(
            "assumptions",
            [f"Aggregated from normalized seed package technical_rules ({batch_label})"],
        )
        record.setdefault("data_gaps", [])

        category = rule.get("rule_category", "")
        name = rule.get("rule_name", "")
        action = rule.get("rule_action")
        condition = rule.get("rule_condition")

        if category in {"processing", "application"}:
            _append_rule_field(
                record,
                "default_mixing_ratio",
                name,
                action.get("mixing_ratio") if isinstance(action, dict) else action,
            )
            _append_rule_field(record, "developer_options", name, action)
            _append_rule_field(
                record,
                "processing_time_ranges",
                name,
                action.get("processing_time_min") if isinstance(action, dict) else None,
            )
        elif category == "lift":
            _append_rule_field(record, "lift_rules", name, action)
        elif category in {"gray_coverage", "neutralization", "intermixing", "color_science", "correction"}:
            _append_rule_field(record, "gray_coverage_rules", name, {"condition": condition, "action": action})
        elif category == "formulation":
            _append_rule_field(record, "special_usage_notes", name, {"condition": condition, "action": action})
        else:
            _append_rule_field(record, "special_usage_notes", name, rule)

    return list(grouped.values())


def build_batch_artifacts(
    pkg: dict[str, Any],
    *,
    batch_number: int,
    batch_label: str,
    shade_filter: Callable[[dict[str, Any]], bool] | None = None,
    rule_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    sources_by_key = source_lookup(pkg.get("sources", []))
    normalized: list[dict[str, Any]] = []

    for seed_shade in pkg.get("shades", []):
        if shade_filter and not shade_filter(seed_shade):
            continue
        key = line_key(seed_shade["brand"], seed_shade.get("product_line"))
        line_cfg = LINE_MAP.get(key)
        if not line_cfg:
            raise KeyError(f"Unmapped seed shade line: {key}")
        normalized.append(
            build_shade_record(seed_shade, line_cfg, sources_by_key, batch_label=batch_label)
        )

    rules = pkg.get("technical_rules", [])
    if rule_filter:
        rules = [rule for rule in rules if rule_filter(rule)]

    tone_ref, tone_norm = build_tone_maps(normalized)
    line_tech = build_line_technical_records(
        rules,
        sources_by_key,
        batch_label=batch_label,
    )

    return {
        "normalized_shade_records": {
            "artifact": "normalized_shade_records",
            "batch": batch_number,
            "count": len(normalized),
            "package_version": pkg.get("metadata", {}).get("package_version"),
            "normalized_shade_records": normalized,
        },
        "tone_normalization_map": {
            "artifact": "tone_normalization_map",
            "batch": batch_number,
            "count": len(tone_norm),
            "tone_normalization_map": tone_norm,
        },
        "manufacturer_tone_reference": {
            "artifact": "manufacturer_tone_reference",
            "batch": batch_number,
            "count": len(tone_ref),
            "manufacturer_tone_reference": tone_ref,
        },
        "line_technical_records": {
            "artifact": "line_technical_records",
            "batch": batch_number,
            "count": len(line_tech),
            "line_technical_records": line_tech,
        },
        "manifest": {
            "batch": batch_number,
            "package_version": pkg.get("metadata", {}).get("package_version"),
            "revision": pkg.get("metadata", {}).get("revision"),
            "shade_records": len(normalized),
            "tone_mappings": len(tone_norm),
            "line_technical_records": len(line_tech),
            "brands": sorted({s["brand"] for s in normalized}),
            "notes": pkg.get("metadata", {}).get("notes"),
        },
    }


def write_batch_artifacts(output_dir: str, artifacts: dict[str, Any], batch_number: int) -> None:
    os.makedirs(output_dir, exist_ok=True)
    mapping = {
        f"normalized_shade_records_batch_{batch_number}.json": artifacts["normalized_shade_records"],
        f"tone_normalization_map_batch_{batch_number}.json": artifacts["tone_normalization_map"],
        f"manufacturer_tone_reference_batch_{batch_number}.json": artifacts["manufacturer_tone_reference"],
        f"line_technical_records_batch_{batch_number}.json": artifacts["line_technical_records"],
        f"batch_{batch_number}_manifest.json": artifacts["manifest"],
    }
    for filename, payload in mapping.items():
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
