#!/usr/bin/env python3
"""Build J_cross_line_conversion_map.json from shade records + curated fixed mappings."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.paths import SHADES_JSON, STAGE12  # noqa: E402
from src.tone_materialization import NON_TRANSLATABLE_SHADE_CODES  # noqa: E402

OUTPUT = STAGE12 / "J_cross_line_conversion_map.json"

AVEDA_CK = "Aveda::Full Spectrum Permanent::US"
SEQ_CK = "Redken::Shades EQ Gloss::US"
VIBRANCE_CK = "Schwarzkopf Professional::IGORA VIBRANCE::US"
MAJIREL_CK = "L'Oréal Professionnel::Majirel::US"

# Initial target lines for Aveda component translation.
AVEDA_TARGET_LINES = [
    MAJIREL_CK,
    VIBRANCE_CK,
    SEQ_CK,
    "Matrix::SoColor::US",
    "Wella Professionals::Koleston Perfect::US",
    "L'Oréal Professionnel::Dia Light::US",
]

# Curated fixed mappings from manufacturer cross-line guides / tone-family equivalence.
FIXED_CONVERSIONS: list[dict] = [
    {
        "conversion_id": "seq_09p__vibrance_9-1",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "09P",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "9-1",
        "mapping_confidence": "medium",
        "source_document": "IGORA VIBRANCE booklet SEQ conversion guide (partial)",
        "notes": "Pearl cool reflect → cendré violet family; no Pearl on VIBRANCE.",
    },
    {
        "conversion_id": "seq_09v__vibrance_9-99",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "09V",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "9-99",
        "mapping_confidence": "high",
        "source_document": "Tone-family equivalence",
        "notes": "Violet → violet.",
    },
    {
        "conversion_id": "seq_07g__vibrance_7-5",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "07G",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "7-5",
        "mapping_confidence": "high",
        "source_document": "Tone-family equivalence",
        "notes": "Gold → gold.",
    },
    {
        "conversion_id": "seq_06cb__vibrance_6-67",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "06CB",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "6-67",
        "mapping_confidence": "high",
        "source_document": "Tone-family equivalence",
        "notes": "Copper brown warm → chocolate/copper.",
    },
    {
        "conversion_id": "seq_07cb__vibrance_7-77",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "07CB",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "7-77",
        "mapping_confidence": "high",
        "source_document": "Tone-family equivalence",
        "notes": "Copper brown → copper.",
    },
    {
        "conversion_id": "seq_04nb__vibrance_4-63",
        "source_canonical_key": SEQ_CK,
        "source_shade_code": "04NB",
        "target_canonical_key": VIBRANCE_CK,
        "strategy": "fixed",
        "target_shade_code": "4-63",
        "mapping_confidence": "low",
        "source_document": "IGORA VIBRANCE booklet (04NB->4-64 likely misprint per G_qa_findings)",
        "notes": "Prefer 4-63 warm brown/gold over nonexistent 4-64.",
    },
]

BOOSTER_PREFIXES = ("Dark ", "Light ", "Pastel ", "ELC + ")
PURE_PIGMENTS = frozenset({"Blue", "Green", "Yellow", "Orange", "Red", "Violet"})


def _component_role(shade_code: str, level: float | None) -> str:
    if shade_code in NON_TRANSLATABLE_SHADE_CODES:
        return "non_color"
    if shade_code.startswith(BOOSTER_PREFIXES) or shade_code in PURE_PIGMENTS:
        return "booster"
    if level is None and shade_code not in PURE_PIGMENTS:
        return "booster"
    return "base"


def _entry_id(source_ck: str, source_code: str, target_ck: str) -> str:
    src = source_ck.split("::")[0].lower().replace("'", "").replace(" ", "_")
    tgt = target_ck.split("::")[1].lower().replace(" ", "_")
    code = re.sub(r"[^a-z0-9]+", "_", source_code.lower()).strip("_")
    return f"{src}_{code}__{tgt}"


def build_aveda_entries(records: list[dict]) -> list[dict]:
    aveda = [r for r in records if r.get("canonical_key") == AVEDA_CK]
    entries: list[dict] = []
    for record in aveda:
        shade_code = record["shade_code"]
        if shade_code in NON_TRANSLATABLE_SHADE_CODES:
            continue
        level = record.get("level")
        role = _component_role(shade_code, level)
        tones = record.get("normalized_tones") or []
        for target_ck in AVEDA_TARGET_LINES:
            entries.append(
                {
                    "conversion_id": _entry_id(AVEDA_CK, shade_code, target_ck),
                    "source_canonical_key": AVEDA_CK,
                    "source_shade_code": shade_code,
                    "target_canonical_key": target_ck,
                    "strategy": "tone_level_match",
                    "target_shade_code": None,
                    "normalized_tones": tones if tones != ["Other"] else None,
                    "level_from": "formula_base" if role == "booster" else "source_shade",
                    "component_role": role,
                    "mapping_confidence": "high" if tones and tones != ["Other"] else "medium",
                    "source_document": record.get("source_document"),
                    "notes": f"Aveda {shade_code} → {target_ck.split('::')[1]} via normalized tone bridge.",
                }
            )
    return entries


def main() -> int:
    records = json.loads(SHADES_JSON.read_text(encoding="utf-8"))["normalized_shade_records"]
    conversions = list(FIXED_CONVERSIONS) + build_aveda_entries(records)
    payload = {
        "artifact": "cross_line_conversion_map",
        "generated": "2026-06-21",
        "completion_status": "partial",
        "count": len(conversions),
        "conversion_entries": conversions,
        "notes": [
            "Path B explicit cross-line translation rules.",
            "strategy=fixed uses target_shade_code directly.",
            "strategy=tone_level_match ranks target catalog by normalized_tones + level.",
            "level_from=formula_base means boosters inherit level from the base shade in the formula.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(conversions)} conversion entries to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
