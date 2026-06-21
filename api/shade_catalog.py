"""Unified shade catalog access for SQLite and PostgreSQL backends."""

from __future__ import annotations

import sqlite3
from typing import Any

from api.backend import db_path, uses_postgres_engine
from api.catalog import search_shades as search_shades_api
from src.matching import ShadeQuery, fetch_shade_candidates


def search_line_shades(
    *,
    line_id: str | None = None,
    query: str | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    return search_shades_api(line_id=line_id, query=query, limit=limit)


def lookup_shade_exact(
    shade_code: str,
    *,
    line_id: str | None = None,
    product_line_hint: str | None = None,
) -> dict[str, Any] | None:
    """Exact shade_code lookup on a line (handles codes with spaces like 'Dark Y/O')."""
    if line_id:
        rows = search_line_shades(line_id=line_id, query=shade_code, limit=50)
        for row in rows:
            if str(row["code"]).lower() == shade_code.lower():
                return _normalize_row(row)
        return None

    if uses_postgres_engine():
        return _lookup_pg_by_code(shade_code, product_line_hint)

    if not db_path().exists():
        return None
    with sqlite3.connect(db_path()) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT s.shade_code, s.shade_name, s.level, pl.product_line_name AS product_line,
                   b.brand_name AS brand
            FROM shade s
            JOIN product_line pl ON pl.line_id = s.line_id
            JOIN brand b ON b.brand_id = pl.brand_id
            WHERE lower(s.shade_code) = lower(?)
        """
        params: list[Any] = [shade_code]
        if product_line_hint:
            sql += " AND lower(pl.product_line_name) LIKE ?"
            params.append(f"%{product_line_hint.lower()}%")
        sql += " LIMIT 1"
        row = conn.execute(sql, params).fetchone()
        if row is None:
            return None
        return {
            "shade_code": row["shade_code"],
            "shade_name": row["shade_name"],
            "level": row["level"],
            "product_line": row["product_line"],
            "brand": row["brand"],
            "normalized_tones": _sqlite_tones(conn, row["shade_code"], row["product_line"]),
        }


def _sqlite_tones(conn: sqlite3.Connection, shade_code: str, product_line: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT snt.tone_name
        FROM shade s
        JOIN product_line pl ON pl.line_id = s.line_id
        JOIN shade_normalized_tone snt ON snt.shade_id = s.shade_id
        WHERE s.shade_code = ? AND pl.product_line_name = ?
        ORDER BY snt.position
        """,
        (shade_code, product_line),
    ).fetchall()
    return [str(r[0]) for r in rows]


def _lookup_pg_by_code(
    shade_code: str,
    product_line_hint: str | None,
) -> dict[str, Any] | None:
    from hair_color_db.production.db import create_session_factory, require_database_url
    from sqlalchemy import select

    from hair_color_db.production.production_models import (
        Brand,
        ProductLine,
        ProductLineRegion,
        Shade,
    )
    from hair_color_db.production.shade_matching import _load_normalized_tones_for_shades

    database_url = require_database_url()
    if not database_url:
        return None
    SessionLocal = create_session_factory(database_url=database_url)
    with SessionLocal() as session:
        stmt = (
            select(
                Shade.shade_id,
                Shade.shade_code,
                Shade.shade_name,
                Shade.level,
                ProductLine.product_line_name,
                Brand.brand_name,
            )
            .join(ProductLineRegion, ProductLineRegion.line_region_id == Shade.line_region_id)
            .join(ProductLine, ProductLine.line_id == ProductLineRegion.line_id)
            .join(Brand, Brand.brand_id == ProductLine.brand_id)
            .where(Shade.shade_code.ilike(shade_code))
        )
        if product_line_hint:
            stmt = stmt.where(ProductLine.product_line_name.ilike(f"%{product_line_hint}%"))
        row = session.execute(stmt.limit(1)).first()
        if row is None:
            return None
        tones = _load_normalized_tones_for_shades(session, [row.shade_id]).get(row.shade_id, set())
        return {
            "shade_code": row.shade_code,
            "shade_name": row.shade_name,
            "level": float(row.level) if row.level is not None else None,
            "product_line": row.product_line_name,
            "brand": row.brand_name,
            "normalized_tones": sorted(tones),
        }


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "shade_code": row["code"],
        "shade_name": row.get("name"),
        "level": row.get("level"),
        "product_line": row.get("line"),
        "brand": row.get("brand"),
        "normalized_tones": row.get("normalized_tones") or [],
    }


def list_shades_for_level(
    line_id: str,
    *,
    level: float | None = None,
    limit: int = 60,
) -> list[dict[str, Any]]:
    shades = search_line_shades(line_id=line_id, limit=limit * 3)
    if level is None:
        return shades[:limit]
    filtered = [
        s
        for s in shades
        if s.get("level") is not None and abs(float(s["level"]) - level) <= 1.0
    ]
    return (filtered or shades)[:limit]


def rank_shades_for_query(
    *,
    product_line: str,
    level: float,
    tones: tuple[str, ...],
    line_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank catalog shades by level + tone fit (SQLite or Postgres)."""
    requested = ShadeQuery(level=float(level), tones=tones)
    if uses_postgres_engine():
        from hair_color_db.production.db import create_session_factory, require_database_url
        from hair_color_db.production.shade_matching import fetch_shade_candidates as fetch_pg

        database_url = require_database_url()
        if not database_url:
            return []
        SessionLocal = create_session_factory(database_url=database_url)
        with SessionLocal() as session:
            matches = fetch_pg(session, requested)
    else:
        if not db_path().exists():
            return []
        with sqlite3.connect(db_path()) as conn:
            matches = fetch_shade_candidates(conn, requested)

    filtered = [
        m
        for m in matches
        if product_line.lower() in str(m.get("line", "")).lower()
    ]
    if line_id and not uses_postgres_engine():
        line_shades = {s["code"] for s in search_line_shades(line_id=line_id, limit=500)}
        filtered = [m for m in filtered if m.get("shade_code") in line_shades] or filtered

    return filtered[:limit]


def format_catalog_for_prompt(shades: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for shade in shades:
        code = shade.get("code") or shade.get("shade_code")
        name = shade.get("name") or shade.get("shade_name")
        level = shade.get("level")
        parts = [str(code)]
        if name:
            parts.append(f"({name})")
        if level is not None:
            parts.append(f"L{level:g}")
        lines.append("- " + " ".join(parts))
    return "\n".join(lines)
