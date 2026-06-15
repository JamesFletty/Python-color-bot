#!/usr/bin/env python3
"""Validate Stage 13 formulation rules package artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hair_color_db.stage13_formulation_rules.validators import format_report, validate_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Stage 13 formulation rules package.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    report = validate_package()
    if args.json:
        payload = {
            "ok": report.ok,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "location": i.location,
                }
                for i in report.issues
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(report))

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
