"""Database-grounded helpers for AI formula translation and parsing."""

from __future__ import annotations

import re
from typing import Any

from api.cross_line_conversion import convert_formula_via_cross_line_map
from api.formula_text_parser import ParsedFormula, enrich_components_from_db, parse_formula_text, source_analysis_summary
from api.shade_catalog import (
    format_catalog_for_prompt,
    list_shades_for_level,
    lookup_shade_exact,
    rank_shades_for_query,
    search_line_shades,
)


def lookup_shade_on_line(
    shade_code: str,
    *,
    product_line_hint: str | None = None,
    line_id: str | None = None,
) -> dict[str, Any] | None:
    return lookup_shade_exact(
        shade_code,
        line_id=line_id,
        product_line_hint=product_line_hint,
    )


def _majirel_aliases(code: str) -> list[str]:
    m = re.fullmatch(r"(\d{1,2})N", code, re.IGNORECASE)
    if m:
        level = int(m.group(1))
        return [f"{level}.0", f"{level}", code]
    return [code]


def _normalize_candidate_codes(shade_code: str, product_line: str) -> list[str]:
    code = shade_code.strip()
    candidates = [code]
    if product_line.lower().startswith("majirel"):
        candidates.extend(_majirel_aliases(code))
    if re.fullmatch(r"\d{1,2}N", code, re.IGNORECASE):
        level = int(code[:-1])
        candidates.append(f"{level}.0")
        candidates.append(f"{level} N/N")
    return list(dict.fromkeys(candidates))


def resolve_shade_for_line(
    shade_code: str,
    *,
    line_id: str,
    product_line: str,
) -> dict[str, Any] | None:
    """Find a catalog row for shade_code on the target line."""
    for candidate in _normalize_candidate_codes(shade_code, product_line):
        exact = lookup_shade_exact(candidate, line_id=line_id)
        if exact:
            return {
                "code": exact["shade_code"],
                "name": exact.get("shade_name"),
                "level": exact.get("level"),
                "line": exact.get("product_line"),
                "brand": exact.get("brand"),
            }
        rows = search_line_shades(line_id=line_id, query=candidate, limit=20)
        for row in rows:
            if str(row["code"]).lower() == candidate.lower():
                return row
    return None


def _is_specialty_subrange_code(shade_code: str) -> bool:
    """True for specialty sub-range codes (e.g. IGORA ROYAL Absolutes 7-470).

    Standard core shades use a 1-2 digit tone suffix (7-0, 7-4, 7-55, 6.46).
    Specialty/anti-aging sub-ranges (Absolutes, etc.) use a 3+ digit tone
    suffix. Those are gray-coverage shades and should not be the default pick
    for a tone/level translation unless nothing else matches.
    """
    code = str(shade_code or "").strip()
    m = re.search(r"[-.\s]([0-9]{3,})$", code)
    return bool(m)


def _deprioritize_specialty(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable-sort core shades ahead of specialty sub-range shades."""
    def code_of(m: dict[str, Any]) -> str:
        return str(m.get("shade_code") or m.get("code") or "")

    return sorted(matches, key=lambda m: _is_specialty_subrange_code(code_of(m)))


def pick_best_target_shade(
    *,
    line_id: str,
    product_line: str,
    parsed_source: ParsedFormula,
    source_canonical_key: str | None = None,
    target_canonical_key: str | None = None,
) -> dict[str, Any] | None:
    """Pick target shade via cross-line conversion map, then tone/level match."""
    if source_canonical_key and target_canonical_key:
        converted = convert_formula_via_cross_line_map(
            parsed_source,
            source_canonical_key=source_canonical_key,
            target_canonical_key=target_canonical_key,
            target_line_id=line_id,
            product_line=product_line,
        )
        if converted:
            return converted

    level = parsed_source.inferred_level or 7.0
    tones = parsed_source.inferred_tones or ("Natural",)
    matches = rank_shades_for_query(
        product_line=product_line,
        level=float(level),
        tones=tones,
        line_id=line_id,
        limit=5,
    )
    if not matches:
        return None
    # Prefer standard core shades over specialty sub-range (e.g. Absolutes)
    # codes, which otherwise surface confusing picks like IGORA ROYAL 7-470.
    matches = _deprioritize_specialty(matches)
    top = matches[0]
    return {
        "code": top["shade_code"],
        "name": top.get("shade_name"),
        "level": top.get("level"),
        "line": top.get("line"),
        "brand": top.get("brand"),
        "normalized_tones": top.get("normalized_tones"),
    }


def build_translation_context(
    source_formula: str,
    source_line: str | None,
    *,
    target_line_id: str,
    target_line: str,
    source_canonical_key: str | None = None,
    target_canonical_key: str | None = None,
) -> dict[str, Any]:
    """Parse source formula and load target-line catalog slice for grounded translation."""
    parsed = enrich_components_from_db(
        parse_formula_text(source_formula),
        line_hint=source_line,
    )
    catalog = list_shades_for_level(target_line_id, level=parsed.inferred_level, limit=50)
    deterministic = pick_best_target_shade(
        line_id=target_line_id,
        product_line=target_line,
        parsed_source=parsed,
        source_canonical_key=source_canonical_key,
        target_canonical_key=target_canonical_key,
    )
    return {
        "parsed_source": parsed,
        "source_summary": source_analysis_summary(parsed),
        "catalog_shades": catalog,
        "catalog_text": format_catalog_for_prompt(catalog[:40]),
        "deterministic_pick": deterministic,
        "conversion_notes": (deterministic or {}).get("conversion_notes"),
    }


def build_parse_context(
    user_input: str,
    *,
    line_id: str,
    color_line: str,
) -> dict[str, Any]:
    """Build catalog context for NL → structured parse on a single line."""
    parsed = enrich_components_from_db(
        parse_formula_text(user_input),
        line_hint=color_line,
    )
    level = parsed.inferred_level
    if level is None:
        for key in ("level", "lvl"):
            m = re.search(rf"(?:natural|current|starting|base|on)\s+{key}\s*(\d{{1,2}})", user_input, re.I)
            if m:
                level = float(m.group(1))
                break
    catalog = list_shades_for_level(line_id, level=level, limit=50)
    deterministic = None
    if level is not None:
        deterministic = pick_best_target_shade(
            line_id=line_id,
            product_line=color_line,
            parsed_source=parsed,
        )
    return {
        "parsed_source": parsed,
        "source_summary": source_analysis_summary(parsed),
        "catalog_shades": catalog,
        "catalog_text": format_catalog_for_prompt(catalog[:40]),
        "deterministic_pick": deterministic,
        "inferred_level": level,
    }


def _is_lazy_natural_alias(shade_code: str, product_line: str) -> bool:
    """Shade codes stylists/LLMs use as 'natural' shortcuts that ignore warmth."""
    if product_line.lower().startswith("majirel"):
        return bool(re.fullmatch(r"\d{1,2}N", shade_code, re.IGNORECASE))
    if re.fullmatch(r"\d{1,2}N", shade_code, re.IGNORECASE):
        return True
    return False


def _source_needs_warmth(context: dict[str, Any]) -> bool:
    parsed = context.get("parsed_source")
    if parsed is None:
        return False
    warm = {"Gold", "Copper", "Red", "Warm", "Auburn"}
    tones = set(parsed.inferred_tones or ())
    return bool(tones & warm)


def ground_structured_result(
    parsed: dict[str, Any],
    *,
    line_id: str,
    product_line: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Validate or replace LLM shade pick with a catalog-backed shade code."""
    shade_code = str(parsed.get("shade") or "").strip()
    skip_alias = _source_needs_warmth(context) and _is_lazy_natural_alias(shade_code, product_line)
    resolved = None if skip_alias else resolve_shade_for_line(
        shade_code, line_id=line_id, product_line=product_line
    )
    if resolved is None:
        deterministic = context.get("deterministic_pick")
        if deterministic:
            parsed["shade"] = deterministic["code"]
            if deterministic.get("level") is not None:
                parsed["desired_level"] = int(float(deterministic["level"]))
            elif context.get("inferred_level") is not None:
                parsed["desired_level"] = int(float(context["inferred_level"]))
            note = (
                f"[Engine grounding] '{shade_code}' not in {product_line} catalog; "
                f"using {deterministic['code']} from tone/level match."
            )
            parsed["grounding_note"] = note
            parsed["_grounded"] = True
            return parsed
        parsed["_grounding_failed"] = shade_code
        return parsed

    parsed["shade"] = resolved["code"]
    if resolved.get("level") is not None:
        parsed["desired_level"] = int(float(resolved["level"]))
    parsed["_grounded"] = True
    return parsed


def ground_translation_result(
    parsed: dict[str, Any],
    *,
    line_id: str,
    product_line: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Validate translation JSON against the target-line catalog."""
    grounded = ground_structured_result(
        parsed,
        line_id=line_id,
        product_line=product_line,
        context=context,
    )
    if grounded.get("grounding_note"):
        grounded["translation_notes"] = (
            f"{grounded.get('translation_notes', '').strip()} {grounded['grounding_note']}"
        ).strip()
    conversion_notes = context.get("conversion_notes")
    if conversion_notes:
        grounded["translation_notes"] = (
            f"{grounded.get('translation_notes', '').strip()} [Cross-line map] {conversion_notes}"
        ).strip()
    return grounded
