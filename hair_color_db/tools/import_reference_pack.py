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


def build_conversion_entries_from_reference() -> list[dict[str, Any]]:
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
    for entry in build_aveda_entries(shades_payload["normalized_shade_records"]):
        add(entry)

    return entries


def import_reference_pack(*, dry_run: bool = False) -> dict[str, Any]:
    shades_payload = json.loads(SHADES_JSON.read_text(encoding="utf-8"))
    records = shades_payload["normalized_shade_records"]

    shade_changes = enrich_shades_from_inventories(records)
    if shade_changes and not dry_run:
        shades_payload["count"] = len(records)
        SHADES_JSON.write_text(
            json.dumps(shades_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    conversions = build_conversion_entries_from_reference()
    conversion_payload = {
        "artifact": "cross_line_conversion_map",
        "generated": "2026-06-21",
        "completion_status": "partial",
        "count": len(conversions),
        "conversion_entries": conversions,
        "notes": [
            "Built from hair_color_db/reference/ manufacturer CSV inventories.",
            "Includes Redken Gels↔SEQ melting pairs, SEQ→VIBRANCE/Majirel tone bridges, Aveda rules.",
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
                {"conversion_count": len(conversions), "shade_records_updated": shade_changes},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return {
        "shade_records_updated": shade_changes,
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
