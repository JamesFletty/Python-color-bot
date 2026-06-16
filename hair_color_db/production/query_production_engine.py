#!/usr/bin/env python3
"""CLI shade matching against PostgreSQL (DATABASE_URL)."""

from __future__ import annotations

import argparse
import json
import os
import sys

from hair_color_db.production.db import create_session_factory, require_database_url
from hair_color_db.production.shade_matching import fetch_shade_candidates
from src.matching import ShadeQuery, normalize_brand_filter


def parse_tones(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(tone.strip() for tone in raw.split(",") if tone.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Query hair color shades by level and tones (PostgreSQL)."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
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

    if not require_database_url(args.database_url):
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    query = ShadeQuery(
        level=args.level,
        tones=parse_tones(args.tones),
        gray_percent=args.gray,
        brand=normalize_brand_filter(args.brand),
    )

    SessionLocal = create_session_factory(database_url=args.database_url)
    with SessionLocal() as session:
        matches = fetch_shade_candidates(session, query)[: args.limit]

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
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
