"""SQLite catalog lookups for brands, lines, and shades."""

from __future__ import annotations

import sqlite3
from typing import Any

from api.backend import db_path, uses_postgres_engine


def _connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(
            f"SQLite catalog not found at {path}. Run `python init_db.py` to build it."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_brands_and_lines() -> list[dict[str, Any]]:
    if uses_postgres_engine():
        from api.catalog_pg import get_brands_and_lines as get_pg_brands
        from hair_color_db.production.db import create_session_factory, require_database_url

        database_url = require_database_url()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when ENGINE_BACKEND=postgres")
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            return get_pg_brands(session)

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.brand_id, b.brand_name,
                   pl.line_id, pl.product_line_name, pl.canonical_key, pl.color_type
            FROM brand b
            JOIN product_line pl ON pl.brand_id = b.brand_id
            ORDER BY b.brand_name, pl.product_line_name
        """)
        brands: dict[int, dict[str, Any]] = {}
        for row in cur.fetchall():
            bid = row["brand_id"]
            if bid not in brands:
                brands[bid] = {"id": str(bid), "name": row["brand_name"], "lines": []}
            brands[bid]["lines"].append({
                "id": str(row["line_id"]),
                "name": row["product_line_name"],
                "key": row["canonical_key"],
                "color_type": row["color_type"],
            })
        return list(brands.values())


def get_line_by_id(line_id: str) -> dict[str, Any] | None:
    if uses_postgres_engine():
        from api.catalog_pg import get_line_by_id as get_pg_line
        from hair_color_db.production.db import create_session_factory, require_database_url

        database_url = require_database_url()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when ENGINE_BACKEND=postgres")
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            return get_pg_line(session, line_id)

    try:
        numeric_line_id = int(line_id)
    except ValueError:
        return None

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT pl.line_id, pl.product_line_name, pl.canonical_key, pl.color_type,
                   b.brand_name
            FROM product_line pl
            JOIN brand b ON b.brand_id = pl.brand_id
            WHERE pl.line_id = ?
        """, (numeric_line_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row["line_id"]),
            "name": row["product_line_name"],
            "key": row["canonical_key"],
            "color_type": row["color_type"],
            "brand": row["brand_name"],
        }


def resolve_canonical_key(line_name: str | None) -> str | None:
    """Resolve a product line display name to its canonical key."""
    if not line_name:
        return None
    needle = line_name.strip().lower()
    for brand in get_brands_and_lines():
        for line in brand["lines"]:
            if line["name"].strip().lower() == needle:
                return line["key"]
    return None


def _resolve_canonical_key_to_id(canonical_key: str) -> int | None:
    """Resolve a canonical key (e.g. 'Aveda::Full Spectrum Permanent::US') to its numeric line_id."""
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT line_id FROM product_line WHERE canonical_key = ? LIMIT 1",
            (canonical_key,),
        )
        row = cur.fetchone()
        return int(row["line_id"]) if row else None


def search_shades(
    line_id: str | None = None,
    query: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    if uses_postgres_engine():
        from api.catalog_pg import search_shades as search_pg_shades
        from hair_color_db.production.db import create_session_factory, require_database_url

        database_url = require_database_url()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when ENGINE_BACKEND=postgres")
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            return search_pg_shades(session, line_id=line_id, query=query, limit=limit)

    numeric_line_id: int | None = None
    if line_id is not None:
        try:
            numeric_line_id = int(line_id)
        except ValueError:
            # line_id may be a canonical key like "Aveda::Full Spectrum Permanent::US"
            # — resolve it to a numeric DB id.
            numeric_line_id = _resolve_canonical_key_to_id(line_id)
            if numeric_line_id is None:
                return []

    with _connect() as conn:
        cur = conn.cursor()
        sql = """
            SELECT s.shade_id, s.shade_code, s.shade_name, s.level,
                   s.color_type, s.sub_range, s.mixing_ratio,
                   pl.product_line_name, b.brand_name
            FROM shade s
            JOIN product_line pl ON pl.line_id = s.line_id
            JOIN brand b ON b.brand_id = pl.brand_id
            WHERE (s.discontinued_status IS NULL
                   OR s.discontinued_status NOT LIKE '%discontinu%')
        """
        params: list[Any] = []
        if numeric_line_id is not None:
            sql += " AND s.line_id = ?"
            params.append(numeric_line_id)
        if query:
            sql += " AND (s.shade_code LIKE ? OR s.shade_name LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        sql += " ORDER BY s.level, s.shade_code LIMIT ?"
        params.append(limit)
        cur.execute(sql, params)
        return [
            {
                "id": str(row["shade_id"]),
                "code": row["shade_code"],
                "name": row["shade_name"],
                "level": row["level"],
                "color_type": row["color_type"],
                "sub_range": row["sub_range"],
                "mixing_ratio": row["mixing_ratio"],
                "line": row["product_line_name"],
                "brand": row["brand_name"],
            }
            for row in cur.fetchall()
        ]
