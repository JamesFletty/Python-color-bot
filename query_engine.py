#!/usr/bin/env python3
"""
CLI shade matching engine for the Phase 1 SQLite hair color database.

Matches shades by level and normalized tones, with optional brand and gray filters.
Returns ranked matches with provenance links. No mixing/developer recommendations.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.logging_utils import configure_logging, log_transformation
from src.matching import ShadeQuery, fetch_shade_candidates, normalize_brand_filter
from src.paths import DEFAULT_DB_PATH


def parse_tones(raw: str | None) -> tuple[str, ...]:
    """Parse comma-separated normalized tone names."""
    if not raw:
        return ()
    return tuple(tone.strip() for tone in raw.split(",") if tone.strip())


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Query hair color shades by level and tones.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path")
    parser.add_argument("--level", type=float, required=True, help="Target shade level")
    parser.add_argument(
        "--tones",
        type=str,
        default="",
        help="Comma-separated normalized tones (e.g. Ash,Blue)",
    )
    parser.add_argument("--gray", type=float, default=None, help="Gray hair percentage")
    parser.add_argument("--brand", type=str, default=None, help="Optional brand filter")
    parser.add_argument("--limit", type=int, default=25, help="Maximum matches to return")
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"Database not found: {args.db}. Run init_db.py first.", file=sys.stderr)
        return 1

    logger = configure_logging()
    query = ShadeQuery(
        level=args.level,
        tones=parse_tones(args.tones),
        gray_percent=args.gray,
        brand=normalize_brand_filter(args.brand),
    )
    log_transformation(
        logger,
        "query_start",
        {
            "level": query.level,
            "tones": list(query.tones),
            "gray_percent": query.gray_percent,
            "brand": query.brand,
        },
    )

    conn = sqlite3.connect(args.db)
    try:
        matches = fetch_shade_candidates(conn, query)[: args.limit]
    finally:
        conn.close()

    result = {
        "query": {
            "level": query.level,
            "tones": list(query.tones),
            "gray_percent": query.gray_percent,
            "brand": query.brand,
        },
        "match_count": len(matches),
        "matches": matches,
    }
    log_transformation(logger, "query_complete", {"match_count": len(matches)})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
