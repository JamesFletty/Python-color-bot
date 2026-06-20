"""SQLite catalog lookups for brands, lines, and shades."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.paths import DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_brands_and_lines() -> list[dict[str, Any]]:
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
                brands[bid] = {"id": bid, "name": row["brand_name"], "lines": []}
            brands[bid]["lines"].append({
                "id": row["line_id"],
                "name": row["product_line_name"],
                "key": row["canonical_key"],
                "color_type": row["color_type"],
            })
        return list(brands.values())


def get_line_by_id(line_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT pl.line_id, pl.product_line_name, pl.canonical_key, pl.color_type,
                   b.brand_name
            FROM product_line pl
            JOIN brand b ON b.brand_id = pl.brand_id
            WHERE pl.line_id = ?
        """, (line_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row["line_id"],
            "name": row["product_line_name"],
            "key": row["canonical_key"],
            "color_type": row["color_type"],
            "brand": row["brand_name"],
        }


def search_shades(
    line_id: int | None = None,
    query: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
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
        if line_id is not None:
            sql += " AND s.line_id = ?"
            params.append(line_id)
        if query:
            sql += " AND (s.shade_code LIKE ? OR s.shade_name LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        sql += " ORDER BY s.level, s.shade_code LIMIT ?"
        params.append(limit)
        cur.execute(sql, params)
        return [
            {
                "id": row["shade_id"],
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
