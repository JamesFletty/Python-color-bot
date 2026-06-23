#!/usr/bin/env python3
"""Export stage12 cross-line conversion map to v2 seed CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from scripts.v2_paths import CROSS_LINE_JSON, CROSS_LINE_MAPPINGS_CSV


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def export_cross_line(path: Path) -> int:
    payload = load_json(CROSS_LINE_JSON)
    entries = payload.get("conversion_entries", [])
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "conversion_id",
        "source_canonical_key",
        "source_shade_code",
        "target_canonical_key",
        "target_shade_code",
        "strategy",
        "mapping_confidence",
        "component_role",
        "normalized_tones",
        "notes",
        "source_document",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for entry in entries:
            tones = entry.get("normalized_tones") or []
            writer.writerow(
                {
                    "conversion_id": entry.get("conversion_id", ""),
                    "source_canonical_key": entry.get("source_canonical_key", ""),
                    "source_shade_code": entry.get("source_shade_code", ""),
                    "target_canonical_key": entry.get("target_canonical_key", ""),
                    "target_shade_code": entry.get("target_shade_code", ""),
                    "strategy": entry.get("strategy", ""),
                    "mapping_confidence": entry.get("mapping_confidence", ""),
                    "component_role": entry.get("component_role", ""),
                    "normalized_tones": "|".join(str(t) for t in tones),
                    "notes": entry.get("notes", ""),
                    "source_document": entry.get("source_document", ""),
                }
            )
    return len(entries)


def main() -> int:
    count = export_cross_line(CROSS_LINE_MAPPINGS_CSV)
    print(f"Wrote {count} cross-line mappings -> {CROSS_LINE_MAPPINGS_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
