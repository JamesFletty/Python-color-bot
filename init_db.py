#!/usr/bin/env python3
"""
Initialize the Phase 1 SQLite database from stage12 package JSON artifacts.

Reads schema_proposal.json for design reference, applies SQLite DDL, loads:
  - normalized shade records (expected: 1,479)
  - tone normalization mappings (expected: 544)
  - line technical rules

Outputs a populated SQLite file and verification report.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.loaders import (
    load_cross_line_conversions,
    load_json,
    load_line_technical_rules,
    load_shades,
    load_tone_mappings,
    validate_counts,
)
from src.logging_utils import configure_logging, log_transformation
from src.paths import DEFAULT_DB_PATH, SCHEMA_PROPOSAL, VERIFICATION_REPORT_PATH
from src.schema import DDL_STATEMENTS


def apply_schema(conn: sqlite3.Connection, logger) -> None:
    """Apply SQLite DDL statements derived from schema_proposal.json."""
    schema_doc = load_json(SCHEMA_PROPOSAL)
    tables = schema_doc["schema_proposal"]["tables"]
    log_transformation(
        logger,
        "schema_reference_loaded",
        {
            "source": str(SCHEMA_PROPOSAL),
            "proposed_tables": tables,
            "ddl_statements_applied": len(DDL_STATEMENTS),
        },
    )
    cursor = conn.cursor()
    for statement in DDL_STATEMENTS:
        cursor.execute(statement)
    conn.commit()


def build_database(db_path: Path, logger) -> dict:
    """Create and populate the SQLite database."""
    if db_path.exists():
        db_path.unlink()
        log_transformation(logger, "removed_existing_database", {"path": str(db_path)})

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        apply_schema(conn, logger)
        load_shades(conn, logger)
        load_tone_mappings(conn, logger)
        load_line_technical_rules(conn, logger)
        load_cross_line_conversions(conn, logger)
        report = validate_counts(conn)
        report["database_path"] = str(db_path.resolve())
        report["status"] = (
            "ok"
            if report["shade_count_ok"] and report["tone_mapping_count_ok"]
            else "validation_failed"
        )
        return report
    finally:
        conn.close()


def write_report(report: dict, report_path: Path) -> None:
    """Write verification report JSON to disk."""
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Initialize hair color SQLite database.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Output SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=VERIFICATION_REPORT_PATH,
        help="Verification report output path",
    )
    args = parser.parse_args(argv)
    logger = configure_logging()

    log_transformation(logger, "init_db_start", {"db_path": str(args.db)})
    report = build_database(args.db, logger)
    write_report(report, args.report)
    log_transformation(logger, "init_db_complete", report)

    print(json.dumps(report, indent=2))
    if report["status"] != "ok":
        print("Validation failed.", file=sys.stderr)
        return 1
    print(f"Database written to {args.db.resolve()}")
    print(f"Verification report written to {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
