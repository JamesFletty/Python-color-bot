#!/usr/bin/env python3
"""
Deterministic formula engine for the Phase 1 SQLite hair color database.

Takes a shade reference and hair condition parameters, reads line_technical_rule
data for mixing ratio, timing, and special notes, and returns a complete formula JSON
with provenance, confidence, and assumptions.

When Stage 13 intake fields are supplied (``--service-intent``, ``--gray``, etc.),
formulation rules from ``hair_color_db/stage13_formulation_rules`` drive the primary
``formula.developer`` and ``formula.mixing_ratio`` outputs. Heuristic developer
selection from line technical rules is used only when Stage 13 rules do not set volume.

Three-part shade references ``Brand::Line::ShadeCode`` resolve the middle segment as
the product line hint (e.g. ``Matrix::SoColor::5N`` targets SoColor Pre-Bonded).

Multi-level darkening responses include ``fill_pigment_guidance`` with inventory-backed
``suggested_shades`` per warm fill level plus ``target_natural_shades`` at the target depth.

Use ``--sub-range`` to override collection rules when the resolved shade record does not
carry the intended sub-range (e.g. ``Extra Coverage``, ``DreamAge``, ``ABSOLUTES``, ``HD``).
When omitted, ``sub_range`` from the matched shade record is applied automatically.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.formula_engine_service import (
    FormulaEngineRequest,
    TERMINAL_STATUSES,
    parse_sub_ranges,
    run_formula_engine,
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    from src.paths import DEFAULT_DB_PATH

    parser = argparse.ArgumentParser(description="Build a hair color formula from shade + conditions.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path")
    parser.add_argument(
        "--shade",
        type=str,
        required=True,
        help='Shade reference (e.g. "Wella 7/1" or "Wella Professionals::Koleston Perfect::7/1")',
    )
    parser.add_argument("--gray", type=float, default=None, help="Gray hair percentage")
    parser.add_argument("--current_level", type=float, default=None, help="Client natural/base level")
    parser.add_argument(
        "--existing-level",
        type=float,
        default=None,
        help="Client current colored level (when different from natural)",
    )
    parser.add_argument(
        "--line",
        type=str,
        default=None,
        help="Optional product line hint when shade code is ambiguous",
    )
    parser.add_argument(
        "--service-intent",
        type=str,
        default="tone_deposit",
        help="Service intent for Stage 13 rule resolution (e.g. gray_coverage, lift_and_tone)",
    )
    parser.add_argument(
        "--desired-level",
        type=float,
        default=None,
        help="Desired result level for lift / Stage 13 rules",
    )
    parser.add_argument(
        "--patch-test-status",
        type=str,
        default="passed",
        choices=["passed", "failed", "declined", "unknown"],
        help="Patch test status for Stage 13 safety gate",
    )
    parser.add_argument("--porosity", type=int, default=5, help="Porosity scale 1-10 for Stage 13 rules")
    parser.add_argument(
        "--sub-range",
        action="append",
        default=None,
        metavar="COLLECTION",
        help=(
            "Product sub-range / collection for Stage 13 line rules (repeatable or comma-separated). "
            "When omitted, inferred from the matched shade record. "
            "Examples: 'Extra Coverage', DreamAge, ABSOLUTES, HD"
        ),
    )
    args = parser.parse_args(argv)

    request = FormulaEngineRequest(
        shade=args.shade,
        gray=args.gray,
        current_level=args.current_level,
        existing_level=args.existing_level,
        line=args.line,
        service_intent=args.service_intent,
        desired_level=args.desired_level,
        patch_test_status=args.patch_test_status,
        porosity=args.porosity,
        sub_ranges=parse_sub_ranges(args.sub_range),
        db_path=args.db,
    )

    try:
        formula = run_formula_engine(request)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(formula, indent=2, ensure_ascii=False))
    return 0 if formula.get("status") in TERMINAL_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())
