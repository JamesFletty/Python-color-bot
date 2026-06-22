"""Explicit cross-line shade conversion rules (Path B)."""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.backend import db_path, uses_postgres_engine
from api.formula_text_parser import ParsedFormula
from api.shade_catalog import lookup_shade_exact, rank_shades_for_query
from src.paths import CROSS_LINE_JSON


def _parse_tones(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return tuple(str(t) for t in parsed)
    except json.JSONDecodeError:
        pass
    return ()


@lru_cache(maxsize=1)
def _load_conversions_from_json() -> list[dict[str, Any]]:
    if not CROSS_LINE_JSON.exists():
        return []
    payload = json.loads(CROSS_LINE_JSON.read_text(encoding="utf-8"))
    return list(payload.get("conversion_entries", []))


def _load_conversions_from_sqlite() -> list[dict[str, Any]]:
    path = db_path()
    if not path.exists():
        return _load_conversions_from_json()
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT conversion_id, source_canonical_key, source_shade_code,
                   target_canonical_key, strategy, target_shade_code,
                   normalized_tones, level_from, component_role,
                   mapping_confidence, source_document, notes
            FROM cross_line_conversion
            """
        ).fetchall()
    if not rows:
        return _load_conversions_from_json()
    return [
        {
            "conversion_id": row["conversion_id"],
            "source_canonical_key": row["source_canonical_key"],
            "source_shade_code": row["source_shade_code"],
            "target_canonical_key": row["target_canonical_key"],
            "strategy": row["strategy"],
            "target_shade_code": row["target_shade_code"],
            "normalized_tones": _parse_tones(row["normalized_tones"]),
            "level_from": row["level_from"],
            "component_role": row["component_role"],
            "mapping_confidence": row["mapping_confidence"],
            "source_document": row["source_document"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def list_conversions() -> list[dict[str, Any]]:
    if uses_postgres_engine():
        return _load_conversions_from_json()
    return _load_conversions_from_sqlite()


def lookup_conversion(
    *,
    source_canonical_key: str,
    source_shade_code: str,
    target_canonical_key: str,
) -> dict[str, Any] | None:
    """Find an explicit conversion rule for a source shade → target line."""
    matches: list[dict[str, Any]] = []
    for entry in list_conversions():
        if (
            entry["source_canonical_key"] == source_canonical_key
            and entry["source_shade_code"].lower() == source_shade_code.lower()
            and entry["target_canonical_key"] == target_canonical_key
        ):
            matches.append(entry)
    if not matches:
        return None
    matches.sort(key=lambda e: 0 if e.get("strategy") == "fixed" else 1)
    return matches[0]


def _formula_base_level(parsed: ParsedFormula) -> float | None:
    levels = [
        float(c.level)
        for c in parsed.components
        if c.level is not None and c.role == "color"
    ]
    if levels:
        return sum(levels) / len(levels)
    return parsed.inferred_level


def _resolve_component_target(
    entry: dict[str, Any],
    *,
    parsed: ParsedFormula,
    target_line_id: str,
    product_line: str,
    grams: int,
) -> dict[str, Any] | None:
    strategy = entry["strategy"]
    if strategy == "fixed" and entry.get("target_shade_code"):
        resolved = lookup_shade_exact(
            entry["target_shade_code"],
            line_id=target_line_id,
        )
        if resolved:
            return {
                "code": resolved["shade_code"],
                "name": resolved.get("shade_name"),
                "level": resolved.get("level"),
                "line": resolved.get("product_line"),
                "brand": resolved.get("brand"),
                "grams": grams,
                "conversion_id": entry["conversion_id"],
                "strategy": "fixed",
            }

    level = parsed.inferred_level or 7.0
    if entry.get("level_from") == "formula_base":
        level = _formula_base_level(parsed) or level
    elif entry.get("level_from") == "source_shade":
        level = parsed.inferred_level or level

    tones = entry.get("normalized_tones") or ()
    if not tones:
        tone_set: list[str] = []
        for comp in parsed.components:
            for tone in comp.normalized_tones:
                if tone not in tone_set and tone != "Other":
                    tone_set.append(tone)
        tones = tuple(tone_set) or ("Natural",)

    matches = rank_shades_for_query(
        product_line=product_line,
        level=float(level),
        tones=tones,
        line_id=target_line_id,
        limit=3,
    )
    if not matches:
        return None
    top = matches[0]
    return {
        "code": top["shade_code"],
        "name": top.get("shade_name"),
        "level": top.get("level"),
        "line": top.get("line"),
        "brand": top.get("brand"),
        "grams": grams,
        "conversion_id": entry["conversion_id"],
        "strategy": "tone_level_match",
        "normalized_tones": top.get("normalized_tones"),
    }


def convert_formula_via_cross_line_map(
    parsed: ParsedFormula,
    *,
    source_canonical_key: str,
    target_canonical_key: str,
    target_line_id: str,
    product_line: str,
) -> dict[str, Any] | None:
    """Translate a parsed formula using explicit cross-line conversion rules."""
    if not parsed.components:
        return None

    component_targets: list[dict[str, Any]] = []
    notes: list[str] = []
    tone_weights: dict[str, float] = {}
    total_grams = 0.0

    for comp in parsed.components:
        if not comp.shade_code:
            continue
        entry = lookup_conversion(
            source_canonical_key=source_canonical_key,
            source_shade_code=comp.shade_code,
            target_canonical_key=target_canonical_key,
        )
        if entry is None:
            continue
        resolved = _resolve_component_target(
            entry,
            parsed=parsed,
            target_line_id=target_line_id,
            product_line=product_line,
            grams=comp.grams,
        )
        if resolved:
            component_targets.append(resolved)
            notes.append(
                f"{comp.grams}g {comp.shade_code} → {resolved['code']} ({entry['strategy']})"
            )
            comp_tones = tuple(comp.normalized_tones) or tuple(entry.get("normalized_tones") or ())
            if not comp_tones or comp_tones == ("Other",):
                comp_tones = tuple(entry.get("normalized_tones") or ())
            for tone in comp_tones:
                if tone == "Other":
                    continue
                tone_weights[tone] = tone_weights.get(tone, 0.0) + float(comp.grams)
            total_grams += float(comp.grams)

    if not component_targets:
        return None

    # Blended tone profile: weight boosters and base together, then rank once on target line.
    if tone_weights and total_grams > 0:
        blended_tones = tuple(
            tone
            for tone, _weight in sorted(
                tone_weights.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        level = _formula_base_level(parsed) or parsed.inferred_level or 7.0
        matches = rank_shades_for_query(
            product_line=product_line,
            level=float(level),
            tones=blended_tones,
            line_id=target_line_id,
            limit=3,
        )
        if matches:
            top = matches[0]
            return {
                "code": top["shade_code"],
                "name": top.get("shade_name"),
                "level": top.get("level"),
                "line": top.get("line"),
                "brand": top.get("brand"),
                "normalized_tones": top.get("normalized_tones"),
                "conversion_notes": "; ".join(notes),
                "conversion_strategy": "blended_tone_level_match",
                "conversion_id": component_targets[0].get("conversion_id"),
                "_via_cross_line_map": True,
                "_blended_tones": blended_tones,
            }

    winner = max(component_targets, key=lambda item: item.get("grams", 0))
    return {
        "code": winner["code"],
        "name": winner.get("name"),
        "level": winner.get("level"),
        "line": winner.get("line"),
        "brand": winner.get("brand"),
        "normalized_tones": winner.get("normalized_tones"),
        "conversion_notes": "; ".join(notes),
        "conversion_strategy": winner.get("strategy"),
        "conversion_id": winner.get("conversion_id"),
        "_via_cross_line_map": True,
    }
