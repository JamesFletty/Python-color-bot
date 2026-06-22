"""Build LLM prompts with v2 catalog context."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.catalog_service import format_catalog_for_prompt
from app.services.cross_line_map import convert_formula_via_cross_line_map
from app.services.formula_text_parser import (
    enrich_components_from_db,
    infer_goal_tones,
    parse_formula_text,
    source_analysis_summary,
)
from app.services.shade_matcher import rank_shade_candidates, resolve_shade


def build_parse_context(
    session: Session,
    user_input: str,
    *,
    line_id: int,
    color_line: str,
) -> dict[str, Any]:
    parsed = parse_formula_text(user_input)
    parsed = enrich_components_from_db(parsed, line_hint=color_line, session=session)
    summary = source_analysis_summary(parsed)

    level = parsed.inferred_level or 7.0
    tones = parsed.inferred_tones or infer_goal_tones(user_input) or ("Natural",)
    ranked = rank_shade_candidates(
        session,
        level=float(level),
        tones=tones,
        limit=5,
    )
    deterministic_pick = ranked[0] if ranked else None

    return {
        "source_summary": summary,
        "catalog_text": format_catalog_for_prompt(session, line_id),
        "deterministic_pick": deterministic_pick,
        "parsed": parsed,
    }


def build_translation_context(
    session: Session,
    source_formula: str,
    *,
    source_canonical_key: str | None,
    target_line_id: int,
    target_line: str,
    target_canonical_key: str,
) -> dict[str, Any]:
    parsed = parse_formula_text(source_formula)
    parsed = enrich_components_from_db(parsed, session=session)
    summary = source_analysis_summary(parsed)

    cross_line_pick = None
    if source_canonical_key:
        cross_line_pick = convert_formula_via_cross_line_map(
            session,
            parsed,
            source_canonical_key=source_canonical_key,
            target_canonical_key=target_canonical_key,
            product_line=target_line,
        )

    level = parsed.inferred_level or 7.0
    tones = parsed.inferred_tones or ("Natural",)
    ranked = rank_shade_candidates(session, level=float(level), tones=tones, limit=5)
    deterministic_pick = cross_line_pick or (ranked[0] if ranked else None)

    return {
        "source_summary": summary,
        "catalog_text": format_catalog_for_prompt(session, target_line_id),
        "deterministic_pick": deterministic_pick,
        "parsed": parsed,
    }


def ground_parsed_result(
    session: Session,
    parsed: dict[str, Any],
    *,
    line_id: int,
    color_line: str,
) -> dict[str, Any]:
    """Ensure shade exists on the target line; substitute nearest ranked match if needed."""
    shade_code = str(parsed.get("shade") or "").strip()
    if not shade_code:
        return parsed

    try:
        resolved = resolve_shade(
            session,
            f"{color_line}::{shade_code}",
            line_hint=color_line,
        )
        parsed["shade"] = f"{resolved.brand}::{resolved.product_line}::{resolved.shade_code}"
        return parsed
    except LookupError:
        pass

    level = parsed.get("desired_level") or parsed.get("current_level") or 7
    tones = tuple(parsed.get("tones") or ()) or ("Natural",)
    matches = rank_shade_candidates(session, level=float(level), tones=tones, limit=1)
    if matches:
        top = matches[0]
        parsed["shade"] = f"{top['brand']}::{top['product_line']}::{top['shade_code']}"
        notes = parsed.get("translation_notes") or ""
        parsed["translation_notes"] = (
            f"Grounded {shade_code} → {top['shade_code']}. {notes}".strip()
        )
    return parsed


def deterministic_parse(
    session: Session,
    user_input: str,
    *,
    color_line: str,
    line_id: int,
) -> dict[str, Any]:
    context = build_parse_context(session, user_input, line_id=line_id, color_line=color_line)
    parsed_formula = context["parsed"]
    pick = context.get("deterministic_pick") or {}

    shade_ref = ""
    if pick:
        shade_ref = f"{pick.get('brand', '')}::{pick.get('product_line', color_line)}::{pick['shade_code']}"
    elif parsed_formula.components:
        code = parsed_formula.components[0].shade_code
        if code:
            shade_ref = f"{color_line}::{code}"

    result = {
        "shade": shade_ref or color_line,
        "current_level": parsed_formula.inferred_level,
        "desired_level": parsed_formula.inferred_level,
        "gray_percent": 0,
        "porosity": 5,
        "elasticity": 6,
        "texture": "medium",
        "service_intent": "tone_deposit",
        "line": color_line,
        "translation_notes": context.get("source_summary"),
    }

    if "gray" in user_input.lower():
        result["service_intent"] = "gray_coverage"
        result["gray_percent"] = 50

    return ground_parsed_result(session, result, line_id=line_id, color_line=color_line)
