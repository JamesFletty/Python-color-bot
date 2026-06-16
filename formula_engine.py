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
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.formula_builder import build_formula
from src.logging_utils import configure_logging, log_transformation
from src.paths import DEFAULT_DB_PATH


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
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
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"Database not found: {args.db}. Run init_db.py first.", file=sys.stderr)
        return 1

    logger = configure_logging()
    log_transformation(
        logger,
        "formula_request",
        {
            "shade": args.shade,
            "gray_percent": args.gray,
            "current_level": args.current_level,
            "line_hint": args.line,
        },
    )

    intake = {
        "service_intent": args.service_intent,
        "patch_test_status": args.patch_test_status,
        "porosity": args.porosity,
    }
    if args.current_level is not None:
        intake["natural_level"] = args.current_level
    if args.existing_level is not None:
        intake["existing_level"] = args.existing_level
    if args.desired_level is not None:
        intake["desired_level"] = args.desired_level

    conn = sqlite3.connect(args.db)
    try:
        formula = build_formula(
            conn,
            shade_ref=args.shade,
            gray_percent=args.gray,
            current_level=args.current_level,
            product_line_hint=args.line,
            intake=intake,
            logger=logger,
        )
    finally:
        conn.close()

    print(json.dumps(formula, indent=2, ensure_ascii=False))
    terminal_statuses = {"ok", "caution"}
    return 0 if formula.get("status") in terminal_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
