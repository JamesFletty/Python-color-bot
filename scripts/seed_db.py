#!/usr/bin/env python3
"""Idempotent PostgreSQL seed loader from v2 CSV artifacts (Phase 2).

Run export scripts first:
  python3 scripts/export_stage12_to_csv.py
  python3 scripts/export_stage13_to_csv.py
  python3 scripts/export_crossline_to_csv.py
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "seed_db.py is a Phase 2 deliverable.\n"
        "Phase 1 complete: run export scripts and audit_stage_data.py first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
