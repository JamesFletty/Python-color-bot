"""Cross-line shade conversion using v2 PostgreSQL catalog."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CrossLineMapping, ProductLine, Shade
from app.services.formula_text_parser import ParsedFormula
from app.services.shade_matcher import rank_shade_candidates, resolve_shade


def lookup_conversion(
    session: Session,
    *,
    source_canonical_key: str,
    source_shade_code: str,
    target_canonical_key: str,
) -> dict[str, Any] | None:
    source_line = session.scalar(
        select(ProductLine).where(ProductLine.canonical_key == source_canonical_key)
    )
    target_line = session.scalar(
        select(ProductLine).where(ProductLine.canonical_key == target_canonical_key)
    )
    if source_line is None or target_line is None:
        return None

    rows = session.scalars(
        select(CrossLineMapping)
        .where(CrossLineMapping.source_line_id == source_line.line_id)
        .where(CrossLineMapping.source_shade_code.ilike(source_shade_code))
        .where(CrossLineMapping.target_line_id == target_line.line_id)
        .order_by(CrossLineMapping.strategy)
    ).all()
    if not rows:
        return None

    row = rows[0]
    return {
        "conversion_id": row.conversion_id,
        "source_canonical_key": source_canonical_key,
        "source_shade_code": row.source_shade_code,
        "target_canonical_key": target_canonical_key,
        "strategy": row.strategy,
        "target_shade_code": row.target_shade_code,
        "normalized_tones": (),
        "mapping_confidence": row.confidence,
        "notes": row.notes,
        "component_role": row.component_role,
    }


def lookup_shade_on_line(
    session: Session,
    shade_code: str,
    *,
    product_line_hint: str | None = None,
) -> dict[str, Any] | None:
    from app.services.repository import EngineRepository

    repo = EngineRepository(session)
    shades = repo.find_shades_by_code(shade_code, line_hint=product_line_hint)
    if not shades:
        return None
    return repo.shade_to_resolved(shades[0])


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
    session: Session,
    entry: dict[str, Any],
    *,
    parsed: ParsedFormula,
    target_canonical_key: str,
    product_line: str,
    grams: int,
) -> dict[str, Any] | None:
    strategy = entry.get("strategy")
    if strategy == "fixed" and entry.get("target_shade_code"):
        try:
            resolved = resolve_shade(
                session,
                f"{target_canonical_key}::{entry['target_shade_code']}",
            )
        except LookupError:
            resolved = None
        if resolved:
            return {
                "code": resolved.shade_code,
                "name": resolved.shade_name,
                "level": resolved.level,
                "line": resolved.product_line,
                "brand": resolved.brand,
                "grams": grams,
                "conversion_id": entry["conversion_id"],
                "strategy": "fixed",
            }

    level = parsed.inferred_level or 7.0
    if entry.get("level_from") == "formula_base":
        level = _formula_base_level(parsed) or level
    elif entry.get("level_from") == "source_shade":
        level = parsed.inferred_level or level

    tones = tuple(entry.get("normalized_tones") or ())
    if not tones:
        tone_set: list[str] = []
        for comp in parsed.components:
            for tone in comp.normalized_tones:
                if tone not in tone_set and tone != "Other":
                    tone_set.append(tone)
        tones = tuple(tone_set) or ("Natural",)

    matches = rank_shade_candidates(
        session,
        level=float(level),
        tones=tones,
        brand=product_line.split("::")[0] if "::" in product_line else None,
        limit=3,
    )
    if not matches:
        return None
    top = matches[0]
    return {
        "code": top["shade_code"],
        "name": top.get("shade_name"),
        "level": top.get("level"),
        "line": top.get("product_line"),
        "brand": top.get("brand"),
        "grams": grams,
        "conversion_id": entry["conversion_id"],
        "strategy": "tone_level_match",
        "normalized_tones": top.get("normalized_tones"),
    }


def convert_formula_via_cross_line_map(
    session: Session,
    parsed: ParsedFormula,
    *,
    source_canonical_key: str,
    target_canonical_key: str,
    product_line: str,
) -> dict[str, Any] | None:
    if not parsed.components:
        return None

    component_targets: list[dict[str, Any]] = []
    notes: list[str] = []

    for comp in parsed.components:
        if not comp.shade_code:
            continue
        entry = lookup_conversion(
            session,
            source_canonical_key=source_canonical_key,
            source_shade_code=comp.shade_code,
            target_canonical_key=target_canonical_key,
        )
        if entry is None:
            continue
        resolved = _resolve_component_target(
            session,
            entry,
            parsed=parsed,
            target_canonical_key=target_canonical_key,
            product_line=product_line,
            grams=comp.grams,
        )
        if resolved:
            component_targets.append(resolved)
            notes.append(
                f"{comp.grams}g {comp.shade_code} → {resolved['code']} ({entry['strategy']})"
            )

    if not component_targets:
        return None

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
