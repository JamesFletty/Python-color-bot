#!/usr/bin/env python3
"""Re-materialize normalized_tones on shade records from F_tone_normalization_map.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.paths import SHADES_JSON, TONE_MAP_JSON  # noqa: E402
from src.tone_materialization import (  # noqa: E402
    build_tone_map_index,
    infer_manufacturer_tone_codes,
    materialize_normalized_tones,
)


def rematerialize(
  *,
  canonical_key_filter: str | None = None,
  dry_run: bool = False,
) -> dict[str, int]:
    shades_payload = json.loads(SHADES_JSON.read_text(encoding="utf-8"))
    tone_payload = json.loads(TONE_MAP_JSON.read_text(encoding="utf-8"))
    tone_index = build_tone_map_index(tone_payload["tone_normalization_map"])

    records = shades_payload["normalized_shade_records"]
    changed = 0
    fixed_other = 0

    for record in records:
        if canonical_key_filter and canonical_key_filter not in record.get("canonical_key", ""):
            continue
        old_tones = list(record.get("normalized_tones") or [])
        old_codes = list(record.get("manufacturer_tone_codes") or [])
        new_codes = infer_manufacturer_tone_codes(record)
        new_tones = materialize_normalized_tones(record, tone_index)

        if new_codes != old_codes:
            record["manufacturer_tone_codes"] = new_codes
        if new_tones != old_tones:
            record["normalized_tones"] = new_tones
            changed += 1
            if old_tones == ["Other"]:
                fixed_other += 1

    if not dry_run and changed:
        shades_payload["count"] = len(records)
        SHADES_JSON.write_text(
            json.dumps(shades_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {"records_changed": changed, "other_fixed": fixed_other, "total": len(records)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-materialize shade normalized_tones from tone map.")
    parser.add_argument("--canonical-key", help="Only update shades for this canonical_key substring")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = rematerialize(canonical_key_filter=args.canonical_key, dry_run=args.dry_run)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
