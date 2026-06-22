#!/usr/bin/env python3
"""Import organized reference CSV/JSON into Stage 12 artifacts and conversion map."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.paths import (  # noqa: E402
    CROSS_LINE_JSON,
    LINE_TECH_JSON,
    SHADES_JSON,
    STAGE12,
    TONE_MAP_JSON,
)

REFERENCE = REPO / "hair_color_db" / "reference"

# Load reference mappings from sibling module
import importlib.util

_mappings_spec = importlib.util.spec_from_file_location(
    "reference_mappings", REFERENCE / "reference_mappings.py"
)
assert _mappings_spec and _mappings_spec.loader
_mappings = importlib.util.module_from_spec(_mappings_spec)
_mappings_spec.loader.exec_module(_mappings)
LINE_CANONICAL = _mappings.LINE_CANONICAL
TONE_FAMILY_TO_NORMALIZED = _mappings.TONE_FAMILY_TO_NORMALIZED
AVEDA_DIRECTION_TO_NORMALIZED = _mappings.AVEDA_DIRECTION_TO_NORMALIZED
LOREAL_FAMILY_TO_NORMALIZED = _mappings.LOREAL_FAMILY_TO_NORMALIZED
BRAND_CONVERSION_SOURCE = _mappings.BRAND_CONVERSION_SOURCE
PRAVANA_CHROMASILK_TARGET = _mappings.PRAVANA_CHROMASILK_TARGET

PRAVANA_REF = REFERENCE / "pravana"

LOREAL_TONE_MAP_LINES: list[tuple[str, str]] = [
    ("L'Oréal Professionnel::Majirel::US", "Majirel"),
    ("L'Oréal Professionnel::Dia Light::US", "Dia Light"),
    ("L'Oréal Professionnel::Dia Richesse::global", "Dia Richesse"),
]

DESCRIPTOR_PART_TO_NORMALIZED: dict[str, list[str]] = {
    "Intense Natural": ["Natural", "Neutral"],
    "Natural": ["Natural"],
    "Ash": ["Ash", "Blue"],
    "Blue": ["Blue", "Ash"],
    "Violet": ["Violet"],
    "Blue-Violet": ["Blue", "Violet"],
    "Blue-Green": ["Blue", "Green"],
    "Iridescent": ["Violet"],
    "Violet-Blue": ["Violet", "Blue"],
    "Violet-Copper": ["Violet", "Copper"],
    "Gold": ["Gold"],
    "Gold-Copper": ["Gold", "Copper"],
    "Copper": ["Copper"],
    "Copper-Gold": ["Copper", "Gold"],
    "Copper-Red": ["Copper", "Red"],
    "Mahogany": ["Mahogany", "Red"],
    "Red": ["Red"],
    "Red-Copper": ["Red", "Copper"],
    "Red-Mahogany": ["Red", "Mahogany"],
    "Matte": ["Green"],
    "Grey": ["Other"],
    "Grey-Violet": ["Violet", "Other"],
    "Brown": ["Brown", "Warm"],
    "Chocolate": ["Brown", "Warm"],
    "Chocolate-Blue": ["Brown", "Blue", "Ash"],
    "Intense Chocolate": ["Brown", "Warm"],
    "Natural-Gold": ["Natural", "Gold"],
    "Natural-Gold-Copper": ["Natural", "Gold", "Copper"],
    "Natural-Red": ["Natural", "Red"],
    "Natural-Blue": ["Natural", "Blue", "Ash"],
    "Natural-Chocolate": ["Natural", "Brown", "Warm"],
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _tone_family_to_normalized(label: str) -> list[str]:
    cleaned = label.strip()
    if not cleaned:
        return ["Other"]
    if cleaned in TONE_FAMILY_TO_NORMALIZED:
        return list(TONE_FAMILY_TO_NORMALIZED[cleaned])
    # split compound families like "Natural/Ash/Gold"
    if "/" in cleaned:
        merged: list[str] = []
        for part in cleaned.split("/"):
            for tone in _tone_family_to_normalized(part):
                if tone not in merged:
                    merged.append(tone)
        return merged or ["Other"]
    return TONE_FAMILY_TO_NORMALIZED.get(cleaned, ["Other"])


def _aveda_booster_alias(shade_code: str) -> str | None:
    """Map inventory shorthand to catalog shade_code."""
    aliases = {
        "6R/O": "6 R/O",
        "5R/O": "5 R/O",
        "4R/O": "4 R/O",
        "3R/O": "3 R/O",
        "6R": "6 R",
        "5R": "5 R",
        "4R": "4 R",
        "3R": "3 R",
        "10N/N": "10 N/N",
        "9N/N": "9 N/N",
        "8N/N": "8 N/N",
        "7N/N": "7 N/N",
        "6N/N": "6 N/N",
        "5N/N": "5 N/N",
        "4N/N": "4 N/N",
        "3N/N": "3 N/N",
    }
    return aliases.get(shade_code.replace(" ", ""))


def _normalize_redken_code(code: str) -> str:
    """Normalize Redken shade codes for cross-line matching (07N ↔ 7N)."""
    m = re.fullmatch(r"0?(\d{1,2})([A-Za-z]+)", code.strip())
    if m:
        return f"{int(m.group(1)):02d}{m.group(2).upper()}"
    return code.strip().upper()


def enrich_shades_from_inventories(records: list[dict[str, Any]]) -> int:
    """Patch normalized_tones on Stage 12 shade records from reference inventories."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["canonical_key"], record["shade_code"])
        index[key] = record

    changed = 0

    # Redken shade inventory
    redken_path = REFERENCE / "redken" / "redken_shade_inventory_1498.csv"
    if redken_path.exists():
        for row in _read_csv(redken_path):
            ck = LINE_CANONICAL.get(row["Color Line"].strip())
            if not ck:
                continue
            code = row["Shade Code"].strip()
            tones = _tone_family_to_normalized(row.get("Tone Family", ""))
            record = index.get((ck, code))
            if record and tones != ["Other"]:
                if record.get("normalized_tones") != tones:
                    record["normalized_tones"] = tones
                    changed += 1

    # Moroccanoil shade inventory
    moroccan_path = REFERENCE / "moroccanoil" / "shade_inventory_b455.csv"
    if moroccan_path.exists():
        for row in _read_csv(moroccan_path):
            ck = LINE_CANONICAL.get(row["Color Line"].strip())
            if not ck:
                continue
            code = row["Shade Code"].strip()
            base_code = code.split("/")[0]
            tones = _tone_family_to_normalized(row.get("Tonal Family", ""))
            record = index.get((ck, code)) or index.get((ck, base_code))
            if record is None:
                for key, rec in index.items():
                    if key[0] == ck and (
                        rec.get("shade_name") == code or key[1] == base_code
                    ):
                        record = rec
                        break
            if record and tones != ["Other"]:
                if record.get("normalized_tones") != tones:
                    record["normalized_tones"] = tones
                    changed += 1

    # Dia Light CSV
    dia_path = REFERENCE / "loreal" / "DIA_Light_Shade_Inventory_d337.csv"
    if dia_path.exists():
        ck = LINE_CANONICAL["Dia Light"]
        for row in _read_csv(dia_path):
            code = row["Shade Code"].split("/")[0].strip()
            family = row.get("Tonal Family", "")
            tones = _tone_family_to_normalized(family)
            primary = row.get("Primary Tone", "").strip()
            if primary:
                extra = LOREAL_FAMILY_TO_NORMALIZED.get(primary.title(), [])
                for tone in extra:
                    if tone not in tones:
                        tones.append(tone)
            record = index.get((ck, code))
            if record and tones != ["Other"]:
                if record.get("normalized_tones") != tones:
                    record["normalized_tones"] = tones
                    changed += 1

    # Aveda shade inventory (formula-based shade codes + tonal direction)
    aveda_inv = REFERENCE / "aveda" / "aveda_shade_inventory_db61.csv"
    if aveda_inv.exists():
        ck = LINE_CANONICAL["Full Spectrum Permanent"]
        for row in _read_csv(aveda_inv):
            code = row["Shade Code"].strip()
            catalog_code = _aveda_booster_alias(code) or code
            direction = row.get("Tonal Direction", "")
            tones = AVEDA_DIRECTION_TO_NORMALIZED.get(direction.strip(), [])
            if not tones:
                tones = _tone_family_to_normalized(row.get("Family", ""))
            record = index.get((ck, catalog_code))
            if record and tones and tones != ["Other"]:
                if record.get("normalized_tones") != tones:
                    record["normalized_tones"] = tones
                    changed += 1

    # Aveda pure tones reference (boosters by Code column)
    pure_path = REFERENCE / "aveda" / "aveda_pure_tones_reference_fba2.csv"
    if pure_path.exists():
        ck = LINE_CANONICAL["Full Spectrum Permanent"]
        from src.tone_materialization import AVEDA_SHADE_CODE_TO_TONE, build_tone_map_index

        tone_payload = json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))
        tone_index = build_tone_map_index(tone_payload["tone_normalization_map"])
        line_tones = tone_index.get(ck, {})
        for row in _read_csv(pure_path):
            code = row["Code"].strip()
            catalog_code = AVEDA_SHADE_CODE_TO_TONE.get(code, code)
            tone_code = AVEDA_SHADE_CODE_TO_TONE.get(code, code)
            if tone_code in line_tones:
                tones = line_tones[tone_code]
            else:
                desc = row.get("Description", "").lower()
                if "gold" in desc and "copper" in desc:
                    tones = ["Gold", "Copper"]
                elif "copper" in desc:
                    tones = ["Copper", "Red"]
                elif "violet" in desc or "ash" in desc:
                    tones = ["Violet", "Ash"]
                elif "red" in desc:
                    tones = ["Red"]
                elif "blue" in desc:
                    tones = ["Blue"]
                else:
                    tones = ["Natural"]
            record = index.get((ck, catalog_code))
            if record and tones:
                if record.get("normalized_tones") != tones:
                    record["normalized_tones"] = tones
                    record["manufacturer_tone_codes"] = [tone_code] if tone_code != catalog_code else record.get("manufacturer_tone_codes", [])
                    changed += 1

    return changed


def _descriptor_to_normalized(descriptor: str, family: str) -> list[str]:
    """Map tonal_reference_key descriptor + family to normalized tone vocabulary."""
    cleaned = descriptor.strip()
    if cleaned in DESCRIPTOR_PART_TO_NORMALIZED:
        return list(DESCRIPTOR_PART_TO_NORMALIZED[cleaned])
    if "-" in cleaned:
        merged: list[str] = []
        for part in cleaned.split("-"):
            for tone in DESCRIPTOR_PART_TO_NORMALIZED.get(part.strip(), []):
                if tone not in merged:
                    merged.append(tone)
        if merged:
            return merged
    return list(LOREAL_FAMILY_TO_NORMALIZED.get(family.strip(), ["Other"]))


def _parse_tonal_reference_code(tone_code: str) -> tuple[str, str]:
    """Parse .03/NG → ('03', 'NG')."""
    body = tone_code.strip().lstrip(".")
    if "/" in body:
        digits, letters = body.split("/", 1)
        return digits, letters
    return body, ""


def enrich_tone_map_from_tonal_reference_key(
    mappings: list[dict[str, Any]],
) -> int:
    """Upsert L'Oréal digit tone codes from shared/tonal_reference_key CSV."""
    ref_path = REFERENCE / "shared" / "tonal_reference_key_561a.csv"
    if not ref_path.exists():
        return 0

    index: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in mappings:
        index[(entry["canonical_key"], entry["manufacturer_tone_code"])] = entry

    changed = 0
    for row in _read_csv(ref_path):
        digit_code, letter_code = _parse_tonal_reference_code(row["Tone Code"])
        descriptor = row.get("Descriptor Name", "").strip()
        family = row.get("Tonal Family", "").strip()
        normalized = _descriptor_to_normalized(descriptor, family)
        manufacturer_term = descriptor or (f".{digit_code}/{letter_code}" if letter_code else f".{digit_code}")

        for canonical_key, product_line in LOREAL_TONE_MAP_LINES:
            key = (canonical_key, digit_code)
            existing = index.get(key)
            if existing:
                preserve = any(
                    note
                    for note in (existing.get("notes") or [])
                    if "Translation target" in str(note) or "cross-line" in str(note).lower()
                )
                if preserve:
                    continue
                updated = False
                if not existing.get("manufacturer_term") and manufacturer_term:
                    existing["manufacturer_term"] = manufacturer_term
                    updated = True
                if existing.get("normalized_tones") in (None, [], ["Other"]) and normalized != ["Other"]:
                    existing["normalized_tones"] = normalized
                    existing["mapping_rationale"] = (
                        f"tonal_reference_key: {row['Tone Code']} ({descriptor})"
                    )
                    existing["mapping_confidence"] = "high"
                    updated = True
                if updated:
                    changed += 1
                continue

            entry = {
                "canonical_key": canonical_key,
                "brand": "L'Oréal Professionnel",
                "product_line": product_line,
                "manufacturer_tone_code": digit_code,
                "manufacturer_term": manufacturer_term,
                "normalized_tones": normalized,
                "mapping_rationale": f"tonal_reference_key: {row['Tone Code']} ({descriptor})",
                "mapping_confidence": "high",
                "ambiguity_flag": False,
                "notes": [f"Imported from tonal_reference_key_561a.csv ({row['Tone Code']})"],
            }
            mappings.append(entry)
            index[key] = entry
            changed += 1

    return changed


def propagate_majirel_digit_map_to_dia_richesse(
    mappings: list[dict[str, Any]],
) -> int:
    """Copy Majirel per-digit decode entries onto Dia Richesse::global."""
    majirel_ck = "L'Oréal Professionnel::Majirel::US"
    richesse_ck = "L'Oréal Professionnel::Dia Richesse::global"
    index: dict[tuple[str, str], dict[str, Any]] = {
        (entry["canonical_key"], entry["manufacturer_tone_code"]): entry for entry in mappings
    }
    changed = 0
    for entry in mappings:
        if entry["canonical_key"] != majirel_ck:
            continue
        code = entry["manufacturer_tone_code"]
        key = (richesse_ck, code)
        existing = index.get(key)
        if existing and existing.get("normalized_tones") not in (None, [], ["Other"]):
            continue
        if existing:
            existing["normalized_tones"] = list(entry["normalized_tones"])
            existing["manufacturer_term"] = entry.get("manufacturer_term")
            existing["mapping_rationale"] = (
                "Propagated from Majirel digit decode via tonal_reference_key import"
            )
            existing["mapping_confidence"] = entry.get("mapping_confidence", "high")
            changed += 1
            continue
        clone = dict(entry)
        clone["canonical_key"] = richesse_ck
        clone["product_line"] = "Dia Richesse"
        clone["mapping_rationale"] = (
            "Propagated from Majirel digit decode via tonal_reference_key import"
        )
        clone["notes"] = list(entry.get("notes") or []) + ["Propagated from Majirel::US"]
        mappings.append(clone)
        index[key] = clone
        changed += 1
    return changed


def _pravana_tones_from_inventory_row(row: dict[str, str]) -> list[str]:
    primary = row.get("primary_tone", "").strip()
    secondary = row.get("secondary_tone", "").strip()
    family = row.get("tone_family", "").strip()
    tones: list[str] = []
    for label in (primary, secondary, family):
        if not label or label.lower() in {"none", "lowlight", "bright", "intense", "sheer"}:
            continue
        for tone in _tone_family_to_normalized(label):
            if tone not in tones:
                tones.append(tone)
    return tones or _tone_family_to_normalized(family)


def _pravana_shade_code_from_inventory(row: dict[str, str]) -> str:
    """Prefer shade_number; naturals use manufacturer code (6N)."""
    shade_number = row.get("shade_number", "").strip()
    code = row.get("code", "").strip()
    if shade_number and "." in shade_number:
        return shade_number
    if shade_number and shade_number.isdigit() and code:
        return code
    return shade_number or code


def _pravana_template_record() -> dict[str, Any]:
    return {
        "canonical_key": PRAVANA_CHROMASILK_TARGET,
        "brand": "Pravana",
        "product_line": "ChromaSilk Crème Color (Permanent)",
        "shade_name": None,
        "manufacturer_tone_descriptions": [],
        "color_type": "permanent",
        "gray_coverage_claim": "Up to 100% gray coverage (ChromaSilk reference pack)",
        "lift_levels": None,
        "mixing_ratio": "1:1.5",
        "developer_options": [
            "ChromaSilk Creme Developer 10V",
            "ChromaSilk Creme Developer 20V",
            "ChromaSilk Creme Developer 30V",
            "ChromaSilk Creme Developer 40V",
        ],
        "processing_time_minutes": 30,
        "special_usage_notes": "Mix 1 part ChromaSilk Creme Color with 1.5 parts Creme Developer.",
        "official_swatch_image_exists": None,
        "region_or_market": "US",
        "discontinued_status": None,
        "source_url": "https://www.pravana.com/pro/chromasilk-creme-hair-color/",
        "source_document": "pravana/chromasilk_shade_inventory.csv",
        "source_type": "manufacturer_reference_pack",
        "source_publication_date": "2026-06-22",
        "source_confidence": "high",
        "evidence_status": "confirmed",
        "assumptions": ["Imported from Pravana reference pack shade inventory."],
        "data_gaps": [],
    }


def add_missing_pravana_shades(records: list[dict[str, Any]]) -> int:
    inv_path = PRAVANA_REF / "chromasilk_shade_inventory.csv"
    if not inv_path.exists():
        return 0
    existing = {
        (r["canonical_key"], r["shade_code"])
        for r in records
        if r.get("canonical_key") == PRAVANA_CHROMASILK_TARGET
    }
    added = 0
    for row in _read_csv(inv_path):
        shade_code = _pravana_shade_code_from_inventory(row)
        if (PRAVANA_CHROMASILK_TARGET, shade_code) in existing:
            continue
        level_raw = row.get("level", "").strip()
        level = float(level_raw) if level_raw else None
        tones = _pravana_tones_from_inventory_row(row)
        tone_code = row.get("code", "").strip()
        record = _pravana_template_record()
        record.update(
            {
                "shade_code": shade_code,
                "shade_name": row.get("description") or row.get("family"),
                "level": level,
                "manufacturer_tone_codes": [tone_code] if tone_code else [],
                "normalized_tones": tones,
            }
        )
        records.append(record)
        existing.add((PRAVANA_CHROMASILK_TARGET, shade_code))
        added += 1
    return added


def enrich_pravana_shades(records: list[dict[str, Any]]) -> int:
    changed = 0
    index: dict[tuple[str, str], dict[str, Any]] = {
        (r["canonical_key"], r["shade_code"]): r for r in records
    }

    inv_path = PRAVANA_REF / "chromasilk_shade_inventory.csv"
    if inv_path.exists():
        for row in _read_csv(inv_path):
            shade_code = _pravana_shade_code_from_inventory(row)
            record = index.get((PRAVANA_CHROMASILK_TARGET, shade_code))
            if not record:
                alt = row.get("code", "").strip()
                record = index.get((PRAVANA_CHROMASILK_TARGET, alt))
            if not record:
                continue
            tones = _pravana_tones_from_inventory_row(row)
            if tones and tones != ["Other"] and record.get("normalized_tones") != tones:
                record["normalized_tones"] = tones
                changed += 1

    express_path = PRAVANA_REF / "express_tones_inventory.csv"
    if express_path.exists():
        ck = LINE_CANONICAL["Express Tones"]
        express_name_map = {
            "ASH": "Ash",
            "BEIGE": "Beige",
            "PEARL": "Pearl",
            "VIOLET": "Violet",
            "CLEAR": "Clear",
        }
        for row in _read_csv(express_path):
            code = row.get("code", "").strip()
            shade_name = express_name_map.get(code)
            if not shade_name:
                continue
            record = index.get((ck, shade_name))
            if not record:
                continue
            base = row.get("base", "").strip()
            tones = _tone_family_to_normalized(base or row.get("tone_family", ""))
            if tones != ["Other"] and record.get("normalized_tones") != tones:
                record["normalized_tones"] = tones
                changed += 1

    return changed


def _build_pravana_code_index(records: list[dict[str, Any]]) -> dict[str, str]:
    """Map conversion-facing codes (6N, 6.3) to catalog shade_code."""
    index: dict[str, str] = {}
    for record in records:
        if record.get("canonical_key") != PRAVANA_CHROMASILK_TARGET:
            continue
        shade_code = str(record.get("shade_code", "")).strip()
        if shade_code:
            index[shade_code.lower()] = shade_code
        for alt in record.get("manufacturer_tone_codes") or []:
            index[str(alt).lower()] = shade_code
    return index


def _parse_chromasilk_target(
    formula: str,
    pravana_index: dict[str, str],
) -> tuple[str | None, str | None]:
    """Return (catalog_shade_code, full_formula_note) for a ChromaSilk conversion."""
    cleaned = formula.strip()
    if not cleaned or cleaned.upper() in {"NA", "N/A"}:
        return None, None
    if "no comparison" in cleaned.lower():
        return None, None

    if ":" in cleaned or re.search(r"\d+\s*pt", cleaned, re.IGNORECASE):
        codes = re.findall(r"(\d+\.?\d*[A-Za-z]*)", cleaned)
        resolved = [pravana_index[c.lower()] for c in codes if c.lower() in pravana_index]
        if not resolved:
            return None, cleaned
        # Prefer fashion/tonal code over plain natural in multi-part mixes.
        non_natural = [c for c in resolved if not re.fullmatch(r"\d+N", c, re.IGNORECASE)]
        target = non_natural[-1] if non_natural else resolved[-1]
        return target, cleaned

    return pravana_index.get(cleaned.lower(), cleaned), None


def build_pravana_brand_conversion_entries(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pravana_index = _build_pravana_code_index(records)
    json_path = PRAVANA_REF / "brand_conversions.json"
    if not json_path.exists():
        return entries

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    for brand_name, brand_data in payload.get("brands", {}).items():
        source_ck = BRAND_CONVERSION_SOURCE.get(brand_name)
        if not source_ck:
            continue
        for conv in brand_data.get("conversions", []):
            source_code = str(conv.get("brand_shade", "")).strip()
            formula = str(conv.get("chromasilk", "")).strip()
            if not source_code or not formula:
                continue
            target_code, formula_note = _parse_chromasilk_target(formula, pravana_index)
            if not target_code:
                continue
            conversion_id = (
                f"{source_ck.split('::')[0].lower()}_{source_code.lower()}__chromasilk"
            )
            notes_parts = [
                conv.get("description", ""),
                brand_data.get("notes", ""),
            ]
            if formula_note:
                notes_parts.insert(0, f"ChromaSilk formula: {formula_note}")
            entries.append(
                {
                    "conversion_id": conversion_id,
                    "source_canonical_key": source_ck,
                    "source_shade_code": source_code,
                    "target_canonical_key": PRAVANA_CHROMASILK_TARGET,
                    "strategy": "fixed",
                    "target_shade_code": target_code,
                    "normalized_tones": [],
                    "level_from": "source_shade",
                    "component_role": "base",
                    "mapping_confidence": "high",
                    "source_document": "pravana/brand_conversions.json",
                    "notes": "; ".join(p for p in notes_parts if p),
                }
            )
    return entries


def enrich_pravana_line_technical(line_records: list[dict[str, Any]]) -> int:
    rules_path = PRAVANA_REF / "formulation_rules.csv"
    creme_path = PRAVANA_REF / "chromasilk_creme_hair_color.json"
    if not rules_path.exists():
        return 0

    by_key = {r["canonical_key"]: r for r in line_records}
    changed = 0
    creme = by_key.get(PRAVANA_CHROMASILK_TARGET)
    if creme:
        gray_rules = []
        for row in _read_csv(rules_path):
            if row.get("category") == "Gray Coverage":
                gray_rules.append(
                    f"{row['rule_name']}: {row['formula']} — {row.get('details', '')}"
                )
        if gray_rules:
            merged = " | ".join(gray_rules)
            if creme.get("gray_coverage_rules") != merged:
                creme["gray_coverage_rules"] = merged
                changed += 1
        mixing = next(
            (r for r in _read_csv(rules_path) if r.get("rule_name") == "ChromaSilk Creme"),
            None,
        )
        if mixing and creme.get("default_mixing_ratio") != mixing.get("formula"):
            creme["default_mixing_ratio"] = mixing["formula"]
            changed += 1

    if creme_path.exists() and creme:
        payload = json.loads(creme_path.read_text(encoding="utf-8"))
        legend = payload.get("numbering_system")
        if legend and not creme.get("tone_family_legend"):
            creme["tone_family_legend"] = json.dumps(legend)
            changed += 1

    express = by_key.get(LINE_CANONICAL["Express Tones"])
    if express:
        mixing = next(
            (r for r in _read_csv(rules_path) if r.get("rule_name") == "Express Tones"),
            None,
        )
        if mixing and express.get("default_mixing_ratio") != mixing.get("formula"):
            express["default_mixing_ratio"] = mixing["formula"]
            changed += 1

    return changed


def build_conversion_entries_from_reference(
    records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate cross-line conversion rules from reference pairing data."""
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(entry: dict[str, Any]) -> None:
        cid = entry["conversion_id"]
        if cid in seen:
            return
        seen.add(cid)
        entries.append(entry)

    seq_ck = LINE_CANONICAL["Shades EQ Gloss"]
    gels_ck = LINE_CANONICAL["Color Gels Lacquers"]
    vibrance_ck = LINE_CANONICAL["IGORA VIBRANCE"]
    majirel_ck = LINE_CANONICAL["Majirel"]
    aveda_ck = LINE_CANONICAL["Full Spectrum Permanent"]

    # Redken Gels ↔ SEQ same-code melting pairing
    redken_path = REFERENCE / "redken" / "redken_shade_inventory_1498.csv"
    if redken_path.exists():
        seq_codes: dict[str, list[str]] = {}
        gels_codes: dict[str, list[str]] = {}
        gels_by_norm: dict[str, str] = {}
        for row in _read_csv(redken_path):
            line = row["Color Line"].strip()
            code = row["Shade Code"].strip()
            tones = _tone_family_to_normalized(row.get("Tone Family", ""))
            if line == "Shades EQ Gloss":
                seq_codes[code] = tones
            elif line == "Color Gels Lacquers":
                gels_codes[code] = tones
                gels_by_norm[_normalize_redken_code(code)] = code

        for seq_code, tones in seq_codes.items():
            norm = _normalize_redken_code(seq_code)
            gels_code = gels_by_norm.get(norm)
            if not gels_code:
                continue
            add(
                {
                    "conversion_id": f"gels_{gels_code.lower()}__seq",
                    "source_canonical_key": gels_ck,
                    "source_shade_code": gels_code,
                    "target_canonical_key": seq_ck,
                    "strategy": "fixed",
                    "target_shade_code": seq_code,
                    "normalized_tones": tones,
                    "level_from": "source_shade",
                    "component_role": "base",
                    "mapping_confidence": "high",
                    "source_document": "redken_color_melting_pairing_2b08.csv",
                    "notes": f"Redken color melt shared code {gels_code} ↔ {seq_code}.",
                }
            )
            add(
                {
                    "conversion_id": f"seq_{seq_code.lower()}__gels",
                    "source_canonical_key": seq_ck,
                    "source_shade_code": seq_code,
                    "target_canonical_key": gels_ck,
                    "strategy": "fixed",
                    "target_shade_code": gels_code,
                    "normalized_tones": gels_codes[gels_code],
                    "level_from": "source_shade",
                    "component_role": "base",
                    "mapping_confidence": "high",
                    "source_document": "redken_color_melting_pairing_2b08.csv",
                    "notes": f"Redken color melt reverse {seq_code} ↔ {gels_code}.",
                }
            )

        # SEQ → IGORA VIBRANCE / Majirel tone-family bridges from inventory
        tone_to_vibrance_hint: dict[str, str] = {
            "Pearl": "9-1",
            "Violet": "9-99",
            "Gold": "9-55",
            "Copper": "7-77",
            "Natural": "9-0",
            "Ash": "9-12",
            "Red": "8-88",
        }
        for code, tones in seq_codes.items():
            level_m = re.match(r"0?(\d{1,2})", code)
            level = int(level_m.group(1)) if level_m else 9
            family_key = next((t for t in tones if t in tone_to_vibrance_hint), tones[0] if tones else "Natural")
            target = tone_to_vibrance_hint.get(family_key, f"{level}-0")
            if level != 9:
                target = target.replace("9-", f"{level}-", 1)
            add(
                {
                    "conversion_id": f"seq_{code.lower()}__vibrance_ref",
                    "source_canonical_key": seq_ck,
                    "source_shade_code": code,
                    "target_canonical_key": vibrance_ck,
                    "strategy": "tone_level_match",
                    "target_shade_code": None,
                    "normalized_tones": tones,
                    "level_from": "source_shade",
                    "component_role": "base",
                    "mapping_confidence": "medium",
                    "source_document": "redken_shade_inventory_1498.csv",
                    "notes": f"Tone-family bridge; hint target {target}.",
                }
            )

        # SEQ → Majirel tone-family bridge
        for code, tones in seq_codes.items():
            add(
                {
                    "conversion_id": f"seq_{code.lower()}__majirel_ref",
                    "source_canonical_key": seq_ck,
                    "source_shade_code": code,
                    "target_canonical_key": majirel_ck,
                    "strategy": "tone_level_match",
                    "target_shade_code": None,
                    "normalized_tones": tones,
                    "level_from": "source_shade",
                    "component_role": "base",
                    "mapping_confidence": "medium",
                    "source_document": "redken_shade_inventory_1498.csv",
                    "notes": "SEQ tone family → Majirel digit notation via shared normalized tones.",
                }
            )

    # Re-import Aveda entries from build_cross_line_conversion_map logic
    from hair_color_db.tools.build_cross_line_conversion_map import (  # noqa: E402
        FIXED_CONVERSIONS,
        build_aveda_entries,
    )

    for entry in FIXED_CONVERSIONS:
        add(entry)

    shades_payload = json.loads(SHADES_JSON.read_text(encoding="utf-8"))
    shade_records = records or shades_payload["normalized_shade_records"]
    for entry in build_aveda_entries(shade_records):
        add(entry)

    for entry in build_pravana_brand_conversion_entries(shade_records):
        add(entry)

    return entries


def import_reference_pack(*, dry_run: bool = False) -> dict[str, Any]:
    shades_payload = json.loads(SHADES_JSON.read_text(encoding="utf-8"))
    records = shades_payload["normalized_shade_records"]

    tone_payload = json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))
    tone_mappings = tone_payload["tone_normalization_map"]
    tone_ref_changes = enrich_tone_map_from_tonal_reference_key(tone_mappings)
    richesse_propagated = propagate_majirel_digit_map_to_dia_richesse(tone_mappings)
    tone_map_changed = tone_ref_changes + richesse_propagated

    pravana_added = add_missing_pravana_shades(records)
    shade_changes = enrich_shades_from_inventories(records) + enrich_pravana_shades(records)

    line_tech_changed = 0
    line_payload: dict[str, Any] = {}
    line_records: list[dict[str, Any]] = []
    if LINE_TECH_JSON.exists():
        line_payload = json.loads(LINE_TECH_JSON.read_text(encoding="utf-8"))
        line_records = line_payload.get("line_technical_records", [])
        line_tech_changed = enrich_pravana_line_technical(line_records)

    rematerialized = 0
    if tone_map_changed and not dry_run:
        tone_payload["count"] = len(tone_mappings)
        TONE_MAP_JSON.write_text(
            json.dumps(tone_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        from hair_color_db.tools.rematerialize_shade_tones_from_map import rematerialize

        rematerialized = rematerialize(dry_run=False)["records_changed"]

    if (shade_changes or pravana_added) and not dry_run:
        shades_payload["count"] = len(records)
        SHADES_JSON.write_text(
            json.dumps(shades_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if line_tech_changed and not dry_run:
        line_payload["count"] = len(line_records)
        LINE_TECH_JSON.write_text(
            json.dumps(line_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    conversions = build_conversion_entries_from_reference(records)
    conversion_payload = {
        "artifact": "cross_line_conversion_map",
        "generated": "2026-06-22",
        "completion_status": "partial",
        "count": len(conversions),
        "conversion_entries": conversions,
        "notes": [
            "Built from hair_color_db/reference/ manufacturer CSV inventories.",
            "Includes Redken Gels↔SEQ melting pairs, SEQ→VIBRANCE/Majirel tone bridges, Aveda rules.",
            "Includes Pravana ChromaSilk brand conversion charts (Goldwell Topchic, Matrix SoColor, Color Insider).",
        ],
    }
    if not dry_run:
        CROSS_LINE_JSON.write_text(
            json.dumps(conversion_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        out_path = REFERENCE / "cross_line" / "generated_conversion_summary.json"
        out_path.write_text(
            json.dumps(
                {
                    "conversion_count": len(conversions),
                    "shade_records_updated": shade_changes,
                    "pravana_shades_added": pravana_added,
                    "line_technical_updated": line_tech_changed,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return {
        "shade_records_updated": shade_changes,
        "pravana_shades_added": pravana_added,
        "line_technical_updated": line_tech_changed,
        "tone_map_entries_changed": tone_map_changed,
        "shade_records_rematerialized": rematerialized,
        "conversion_entries": len(conversions),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import reference pack into Stage 12 artifacts.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = import_reference_pack(dry_run=args.dry_run)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
