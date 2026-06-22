"""Shade matching and ranking for query_engine."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ShadeQuery:
    """Normalized shade search parameters."""

    level: float
    tones: tuple[str, ...]
    gray_percent: float | None = None
    brand: str | None = None


def normalize_brand_filter(brand: str | None) -> str | None:
    """Normalize optional brand filter for case-insensitive matching."""
    if brand is None:
        return None
    cleaned = brand.strip()
    return cleaned or None


def brand_matches(candidate: str, requested: str | None) -> bool:
    """Return True when requested brand filter matches candidate brand name."""
    if requested is None:
        return True
    candidate_lower = candidate.lower()
    requested_lower = requested.lower()
    return (
        requested_lower in candidate_lower
        or candidate_lower in requested_lower
        or requested_lower.replace(" ", "") in candidate_lower.replace(" ", "")
    )


def score_shade(
    *,
    requested: ShadeQuery,
    shade_level: float | None,
    shade_tones: set[str],
    shade_gray_claim: str | None,
    has_gray_rules: bool,
) -> tuple[float, dict[str, Any]]:
    """Compute a deterministic match score and score breakdown."""
    breakdown: dict[str, Any] = {
        "level_match": 0.0,
        "tone_matches": [],
        "tone_score": 0.0,
        "gray_bonus": 0.0,
    }
    if shade_level is None:
        return 0.0, breakdown

    level_delta = abs(shade_level - requested.level)
    if level_delta == 0:
        breakdown["level_match"] = 40.0
    elif level_delta <= 0.5:
        breakdown["level_match"] = 25.0
    elif level_delta <= 1.0:
        breakdown["level_match"] = 10.0
    else:
        return 0.0, breakdown

    if not requested.tones:
        breakdown["tone_score"] = 20.0
    else:
        per_tone = 60.0 / len(requested.tones)
        for tone in requested.tones:
            if tone in shade_tones:
                breakdown["tone_matches"].append(tone)
                breakdown["tone_score"] += per_tone

    if requested.gray_percent and requested.gray_percent > 0:
        if shade_gray_claim:
            breakdown["gray_bonus"] += 5.0
        if has_gray_rules:
            breakdown["gray_bonus"] += 5.0

    total = breakdown["level_match"] + breakdown["tone_score"] + breakdown["gray_bonus"]
    return round(total, 2), breakdown


def fetch_shade_candidates(
    conn: sqlite3.Connection,
    requested: ShadeQuery,
) -> list[dict[str, Any]]:
    """Query SQLite for shade candidates and return ranked matches."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    level_min = requested.level - 1.0
    level_max = requested.level + 1.0
    cursor.execute(
        """
        SELECT
            s.shade_id,
            s.canonical_key,
            s.shade_code,
            s.shade_name,
            s.sub_range,
            s.level,
            s.gray_coverage_claim,
            s.source_url,
            s.source_document,
            s.source_confidence,
            s.evidence_status,
            b.brand_name AS brand,
            pl.product_line_name AS product_line,
            pl.line_id,
            GROUP_CONCAT(snt.tone_name, ',') AS tone_csv
        FROM shade s
        JOIN product_line pl ON pl.line_id = s.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        LEFT JOIN shade_normalized_tone snt ON snt.shade_id = s.shade_id
        WHERE s.level IS NOT NULL
          AND s.level BETWEEN ? AND ?
        GROUP BY s.shade_id
        """,
        (level_min, level_max),
    )

    line_ids: set[int] = set()
    rows = cursor.fetchall()
    for row in rows:
        line_ids.add(int(row["line_id"]))

    gray_rule_lines: set[int] = set()
    if line_ids:
        placeholders = ",".join("?" for _ in line_ids)
        cursor.execute(
            f"""
            SELECT DISTINCT line_id
            FROM line_technical_rule
            WHERE rule_type = 'gray_coverage' AND line_id IN ({placeholders})
            """,
            tuple(line_ids),
        )
        gray_rule_lines = {int(row[0]) for row in cursor.fetchall()}

    matches: list[dict[str, Any]] = []
    for row in rows:
        brand = str(row["brand"])
        if not brand_matches(brand, requested.brand):
            continue

        tone_csv = row["tone_csv"] or ""
        shade_tones = {tone.strip() for tone in tone_csv.split(",") if tone.strip()}
        score, breakdown = score_shade(
            requested=requested,
            shade_level=float(row["level"]) if row["level"] is not None else None,
            shade_tones=shade_tones,
            shade_gray_claim=row["gray_coverage_claim"],
            has_gray_rules=int(row["line_id"]) in gray_rule_lines,
        )
        if score <= 0:
            continue

        provenance_links = []
        if row["source_url"]:
            provenance_links.append(
                {
                    "role": "primary",
                    "url": row["source_url"],
                    "document": row["source_document"],
                    "confidence": row["source_confidence"],
                    "evidence_status": row["evidence_status"],
                }
            )

        matches.append(
            {
                "shade_code": row["shade_code"],
                "shade_name": row["shade_name"],
                "sub_range": row["sub_range"] or None,
                "brand": brand,
                "line": row["product_line"],
                "canonical_key": row["canonical_key"],
                "level": row["level"],
                "normalized_tones": sorted(shade_tones),
                "match_score": score,
                "score_breakdown": breakdown,
                "provenance_links": provenance_links,
            }
        )

    matches.sort(
        key=lambda item: (
            -item["match_score"],
            item["brand"],
            item["line"],
            item["shade_code"],
        )
    )
    return matches


def parse_shade_reference(shade_ref: str) -> tuple[str | None, str | None, str]:
    """
    Parse a shade reference like 'Wella 7/1' or 'Wella Professionals::Koleston Perfect::7/1'.

    Returns (brand_hint, product_line_hint, shade_code).
    Three-part ``Brand::Line::ShadeCode`` references include the middle segment as the line hint.
    """
    cleaned = shade_ref.strip()
    if "::" in cleaned:
        parts = [part.strip() for part in cleaned.split("::") if part.strip()]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[-1]
        if len(parts) >= 2:
            return parts[0], None, parts[-1]

    # Shade codes with spaces (e.g. Aveda "7 N/N", "Light N/N", "8 O/R") must not
    # be split — treat the whole string as the shade code whenever the last token
    # contains a "/" (the separator used in Aveda-style compound codes).
    tokens = cleaned.split()
    if len(tokens) == 2 and "/" in tokens[1]:
        return None, None, cleaned

    if len(tokens) >= 2:
        shade_code = tokens[-1]
        brand_hint = " ".join(tokens[:-1])
        return brand_hint, None, shade_code

    return None, None, cleaned


def _is_permanent_color_type(color_type: str | None) -> bool:
    """Return True for permanent (non-demi) color types."""
    if not color_type:
        return False
    lowered = color_type.lower()
    if "demi" in lowered:
        return False
    return "permanent" in lowered


def lookup_shade_by_reference(
    conn: sqlite3.Connection,
    shade_ref: str,
    *,
    product_line_hint: str | None = None,
) -> dict[str, Any] | None:
    """Resolve a shade reference to a single best-matching shade row."""
    conn.row_factory = sqlite3.Row
    brand_hint, line_hint_from_ref, shade_code = parse_shade_reference(shade_ref)
    effective_line_hint = product_line_hint or line_hint_from_ref
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            s.*,
            b.brand_name AS brand,
            pl.product_line_name AS product_line
        FROM shade s
        JOIN product_line pl ON pl.line_id = s.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        WHERE s.shade_code = ?
        ORDER BY
            CASE
                WHEN lower(COALESCE(s.color_type, '')) LIKE '%demi%' THEN 1
                WHEN lower(COALESCE(s.color_type, '')) LIKE '%permanent%' THEN 0
                ELSE 2
            END,
            pl.product_line_name,
            s.sub_range
        """,
        (shade_code,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    if not rows:
        return None

    filtered = rows
    if brand_hint:
        filtered = [row for row in rows if brand_matches(str(row["brand"]), brand_hint)]
        if not filtered:
            filtered = rows

    if effective_line_hint:
        line_filtered = [
            row
            for row in filtered
            if effective_line_hint.lower() in str(row["product_line"]).lower()
        ]
        if not line_filtered:
            return None
        filtered = line_filtered

    # Prefer permanent lines when multiple matches remain (e.g. Wella 7/1).
    permanent = [
        row for row in filtered if _is_permanent_color_type(row.get("color_type"))
    ]
    if permanent:
        filtered = permanent

    chosen = filtered[0]
    cursor.execute(
        """
        SELECT tone_name
        FROM shade_normalized_tone
        WHERE shade_id = ?
        ORDER BY position
        """,
        (chosen["shade_id"],),
    )
    chosen["normalized_tones"] = [row[0] for row in cursor.fetchall()]
    for json_field in (
        "developer_options",
        "manufacturer_tone_codes",
        "manufacturer_tone_descriptions",
        "assumptions",
        "data_gaps",
    ):
        raw = chosen.get(json_field)
        if isinstance(raw, str) and raw:
            chosen[json_field] = json.loads(raw)
    return chosen


def fetch_line_rules(
    conn: sqlite3.Connection,
    line_id: int,
) -> dict[str, Any]:
    """Fetch all line technical rules for a product line keyed by rule_type."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rule_type, rule_value, source_url, source_document,
               source_confidence, evidence_status, assumptions, data_gaps
        FROM line_technical_rule
        WHERE line_id = ?
        ORDER BY rule_id
        """,
        (line_id,),
    )
    rules: dict[str, Any] = {}
    for row in cursor.fetchall():
        rule_type = row["rule_type"]
        value = json.loads(row["rule_value"])
        entry = {
            "value": value,
            "source_url": row["source_url"],
            "source_document": row["source_document"],
            "source_confidence": row["source_confidence"],
            "evidence_status": row["evidence_status"],
            "assumptions": json.loads(row["assumptions"]) if row["assumptions"] else [],
            "data_gaps": json.loads(row["data_gaps"]) if row["data_gaps"] else [],
        }
        rules.setdefault(rule_type, []).append(entry)
    return rules
