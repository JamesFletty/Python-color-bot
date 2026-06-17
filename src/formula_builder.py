"""Deterministic formula assembly from shade + line technical rules."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from src.logging_utils import log_transformation
from src.matching import fetch_line_rules, lookup_shade_by_reference

_VOLUME_OPTION_PATTERNS: dict[int, tuple[str, ...]] = {
    10: (r"10\s*vol", r"3\s*%"),
    20: (r"20\s*vol", r"6\s*%"),
    30: (r"30\s*vol", r"9\s*%"),
    40: (r"40\s*vol", r"12\s*%"),
}


def _option_is_multi_volume_chart(text: str) -> bool:
    """Return True when an option lists multiple developer volumes (line chart text)."""
    return len(re.findall(r"\d+\s*vol", text, re.IGNORECASE)) > 1


def format_developer_volume(
    volume: int,
    developer_options: list[str] | None = None,
) -> str:
    """Map a Stage 13 developer volume to a salon-facing developer label."""
    if developer_options:
        for option in developer_options:
            if _option_is_multi_volume_chart(option):
                continue
            option_lower = option.lower()
            for pattern in _VOLUME_OPTION_PATTERNS.get(volume, ()):
                if re.search(pattern, option_lower, re.IGNORECASE):
                    return option
            if re.search(rf"\b{volume}\s*vol\b", option_lower, re.IGNORECASE):
                return option
    return f"{volume} vol"


def apply_stage13_formulation_overlay(
    formula: dict[str, Any],
    stage13_result: Any,
    *,
    developer_options: list[str] | None,
    heuristic_developer: str | None,
) -> None:
    """Promote Stage 13 rule outputs into primary formula fields when rules apply."""
    formula_block = formula.setdefault("formula", {})
    assumptions = formula.setdefault("assumptions", [])

    if stage13_result.developer_volume is not None:
        rule_developer = format_developer_volume(
            int(stage13_result.developer_volume),
            developer_options=developer_options,
        )
        formula_block["developer"] = rule_developer
        formula_block["developer_rationale"] = [
            (
                f"Stage 13 rule(s) {', '.join(stage13_result.matched_rules)} "
                f"set developer to {stage13_result.developer_volume} vol."
            )
        ]
        if heuristic_developer and heuristic_developer != rule_developer:
            assumptions.append(
                "Heuristic developer selection overridden by Stage 13 formulation rule match."
            )
    elif stage13_result.matched_rules and heuristic_developer is None:
        formula_block["developer"] = None

    if stage13_result.mixing_ratio:
        formula_block["mixing_ratio"] = stage13_result.mixing_ratio

    if stage13_result.natural_shade_ratio is not None:
        formula_block["natural_shade_ratio"] = stage13_result.natural_shade_ratio

    if getattr(stage13_result, "fill_pigment_guidance", None):
        formula_block["fill_pigment_guidance"] = stage13_result.fill_pigment_guidance

    deposit_levels = getattr(stage13_result, "deposit_levels", 0)
    if deposit_levels:
        formula.setdefault("hair_conditions", {})["deposit_levels"] = deposit_levels


def _first_rule_value(rules: dict[str, Any], rule_type: str) -> Any:
    """Return the first stored value for a rule type."""
    entries = rules.get(rule_type) or []
    if not entries:
        return None
    return entries[0]["value"]


def _rule_provenance(rules: dict[str, Any], rule_type: str) -> list[dict[str, Any]]:
    """Collect provenance links for a rule type."""
    links: list[dict[str, Any]] = []
    for entry in rules.get(rule_type) or []:
        if entry.get("source_url"):
            links.append(
                {
                    "rule_type": rule_type,
                    "url": entry["source_url"],
                    "document": entry["source_document"],
                    "confidence": entry["source_confidence"],
                    "evidence_status": entry["evidence_status"],
                }
            )
    return links


def _parse_percent_from_text(text: str) -> float | None:
    """Extract the first percentage value from free text."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1))


def select_developer(
    *,
    developer_options: list[str] | None,
    developer_strengths: list[str] | None,
    gray_percent: float | None,
    current_level: float | None,
    target_level: float | None,
) -> dict[str, Any]:
    """
    Select developer strength using line rules and hair condition parameters.

    Developer choice is deterministic and rule-driven; when multiple rules apply,
    the strongest applicable guidance wins with assumptions recorded.
    """
    assumptions: list[str] = []
    warnings: list[str] = []
    selected: str | None = None
    rationale: list[str] = []

    lift_delta = None
    if current_level is not None and target_level is not None:
        lift_delta = target_level - current_level

    strengths = developer_strengths or []
    options = developer_options or []

    if gray_percent is not None and gray_percent > 0:
        for rule_text in strengths:
            lower = rule_text.lower()
            if "grey" in lower or "gray" in lower:
                if "coverage" in lower or "cover" in lower:
                    if gray_percent >= 30:
                        for option in options:
                            if "6%" in option or "20 vol" in option.lower():
                                selected = option
                                rationale.append(
                                    f"Gray coverage {gray_percent}% maps to 6% developer per line rule: {rule_text}"
                                )
                                break
                    if selected:
                        break

    if selected is None and lift_delta is not None:
        if lift_delta <= 0:
            for option in options:
                if "4%" in option or "13 vol" in option.lower():
                    selected = option
                    rationale.append(
                        "No lift required; selected 4% developer per lift rule for same depth or darker."
                    )
                    break
        elif lift_delta <= 1:
            for option in options:
                if "6%" in option or "20 vol" in option.lower():
                    selected = option
                    rationale.append(
                        f"Lift delta {lift_delta} level(s) maps to 6% developer per line lift rules."
                    )
                    break
        elif lift_delta <= 2:
            for option in options:
                if "9%" in option or "30 vol" in option.lower():
                    selected = option
                    rationale.append(
                        f"Lift delta {lift_delta} level(s) maps to 9% developer per line lift rules."
                    )
                    break
        else:
            for option in options:
                if "12%" in option or "40 vol" in option.lower():
                    selected = option
                    rationale.append(
                        f"Lift delta {lift_delta} level(s) maps to 12% developer per line lift rules."
                    )
                    break

    if selected is None and options:
        selected = options[0]
        assumptions.append(
            "Developer selected as first listed line option because no gray/lift rule produced a match."
        )

    if selected is None:
        warnings.append("No developer options available for this shade/line.")

    return {
        "developer": selected,
        "rationale": rationale,
        "assumptions": assumptions,
        "warnings": warnings,
    }


def select_processing_time(processing_rules: list[str] | None, gray_percent: float | None) -> dict[str, Any]:
    """Pick a processing time range from line technical rules."""
    if not processing_rules:
        return {
            "processing_time": None,
            "assumptions": ["No processing time rules found for this line."],
        }

    chosen = processing_rules[0]
    assumptions: list[str] = []

    if gray_percent and gray_percent > 0:
        for rule in processing_rules:
            lower = rule.lower()
            if "grey" in lower or "gray" in lower:
                chosen = rule
                assumptions.append("Selected gray-specific processing time rule.")
                break

    return {"processing_time": chosen, "assumptions": assumptions}


def select_gray_coverage_adjustment(
    gray_rules: list[str] | None,
    gray_percent: float | None,
    shade_code: str,
) -> dict[str, Any]:
    """Return gray blending guidance when applicable."""
    if not gray_rules or gray_percent is None or gray_percent <= 0:
        return {"gray_coverage_guidance": None, "assumptions": []}

    guidance = None
    assumptions: list[str] = []

    for rule in gray_rules:
        lower = rule.lower()
        if "30-50%" in lower or "30%" in lower and "50%" in lower:
            if 30 <= gray_percent < 50:
                guidance = rule
                assumptions.append("Applied 30-50% gray coverage blending rule.")
                break
        if "50-100%" in lower or ("50%" in lower and "100%" in lower):
            if gray_percent >= 50:
                guidance = rule
                assumptions.append("Applied 50-100% gray coverage blending rule.")
                break

    if guidance is None:
        for rule in gray_rules:
            if "6%" in rule or "coverage" in rule.lower():
                guidance = rule
                assumptions.append(
                    f"No exact gray-band rule matched {gray_percent}%; using general gray coverage rule."
                )
                break

    return {
        "gray_coverage_guidance": guidance,
        "assumptions": assumptions,
        "example_natural_shade": shade_code.split("/")[0] + "/0" if "/" in shade_code else None,
    }


def build_formula(
    conn: sqlite3.Connection,
    *,
    shade_ref: str,
    gray_percent: float | None = None,
    current_level: float | None = None,
    product_line_hint: str | None = None,
    intake: dict[str, Any] | None = None,
    logger: Any | None = None,
) -> dict[str, Any]:
    """Build a complete formula JSON document for a shade and hair conditions."""
    shade = lookup_shade_by_reference(
        conn,
        shade_ref,
        product_line_hint=product_line_hint,
    )
    if shade is None:
        return {
            "status": "error",
            "error": f"Shade not found for reference: {shade_ref}",
            "assumptions": [],
            "confidence": "unresolved",
        }

    rules = fetch_line_rules(conn, int(shade["line_id"]))
    target_level = float(shade["level"]) if shade.get("level") is not None else None

    mixing_ratio = shade.get("mixing_ratio") or _first_rule_value(rules, "mixing_ratio")
    developer_options = shade.get("developer_options")
    if not developer_options:
        developer_blob = _first_rule_value(rules, "developer")
        if isinstance(developer_blob, list):
            developer_options = developer_blob

    developer_strengths = None
    developer_entries = rules.get("developer") or []
    for entry in developer_entries:
        value = entry["value"]
        if isinstance(value, list) and any("lift" in str(item).lower() for item in value):
            developer_strengths = value
            break

    starting_level = current_level
    desired_level = target_level
    natural_level = current_level
    existing_level = None
    if intake is not None:
        natural_level = intake.get("natural_level", current_level)
        existing_level = intake.get("existing_level")
        if existing_level is not None:
            starting_level = existing_level
        elif natural_level is not None:
            starting_level = natural_level
        if intake.get("desired_level") is not None:
            desired_level = float(intake["desired_level"])
        elif target_level is not None:
            desired_level = target_level

    developer_selection = select_developer(
        developer_options=developer_options,
        developer_strengths=developer_strengths,
        gray_percent=gray_percent,
        current_level=starting_level,
        target_level=desired_level,
    )
    processing = select_processing_time(_first_rule_value(rules, "processing_time"), gray_percent)
    gray_guidance = select_gray_coverage_adjustment(
        _first_rule_value(rules, "gray_coverage"),
        gray_percent,
        str(shade["shade_code"]),
    )

    special_notes: list[str] = []
    special_blob = _first_rule_value(rules, "special_usage")
    if isinstance(special_blob, list):
        special_notes.extend(special_blob)
    if shade.get("special_usage_notes"):
        special_notes.append(str(shade["special_usage_notes"]))

    unresolved_tones = []
    manufacturer_codes = shade.get("manufacturer_tone_codes") or []
    normalized_tones = shade.get("normalized_tones") or []
    if manufacturer_codes and not normalized_tones:
        unresolved_tones.extend(manufacturer_codes)

    assumptions: list[str] = []
    for field in ("assumptions",):
        raw = shade.get(field)
        if isinstance(raw, list):
            assumptions.extend(str(item) for item in raw)
    assumptions.extend(developer_selection["assumptions"])
    assumptions.extend(processing["assumptions"])
    assumptions.extend(gray_guidance["assumptions"])

    data_gaps = shade.get("data_gaps") or []
    for entry in rules.get("mixing_ratio", []):
        data_gaps.extend(entry.get("data_gaps") or [])

    provenance_links = []
    if shade.get("source_url"):
        provenance_links.append(
            {
                "role": "shade_primary",
                "url": shade["source_url"],
                "document": shade.get("source_document"),
                "confidence": shade.get("source_confidence"),
                "evidence_status": shade.get("evidence_status"),
            }
        )
    for rule_type in ("mixing_ratio", "developer", "processing_time", "gray_coverage", "lift"):
        provenance_links.extend(_rule_provenance(rules, rule_type))

    confidence = shade.get("source_confidence") or "unresolved"
    if unresolved_tones:
        confidence = "medium" if confidence == "high" else confidence

    formula = {
        "status": "ok",
        "shade": {
            "shade_code": shade["shade_code"],
            "shade_name": shade.get("shade_name"),
            "sub_range": shade.get("sub_range") or None,
            "brand": shade["brand"],
            "product_line": shade["product_line"],
            "canonical_key": shade["canonical_key"],
            "level": target_level,
            "normalized_tones": normalized_tones,
            "manufacturer_tone_codes": manufacturer_codes,
            "color_type": shade.get("color_type"),
        },
        "hair_conditions": {
            "gray_percent": gray_percent,
            "natural_level": natural_level,
            "existing_level": existing_level,
            "current_level": starting_level,
            "target_level": target_level,
            "desired_level": desired_level,
            "lift_delta": (
                desired_level - starting_level
                if desired_level is not None and starting_level is not None
                else None
            ),
            "deposit_levels": (
                max(0.0, starting_level - desired_level)
                if desired_level is not None and starting_level is not None
                else None
            ),
        },
        "formula": {
            "mixing_ratio": mixing_ratio,
            "developer": developer_selection["developer"],
            "developer_rationale": developer_selection["rationale"],
            "processing_time": processing["processing_time"],
            "gray_coverage_guidance": gray_guidance["gray_coverage_guidance"],
            "special_usage_notes": special_notes,
        },
        "unresolved_tones": unresolved_tones,
        "warnings": developer_selection["warnings"],
        "assumptions": assumptions,
        "data_gaps": data_gaps,
        "confidence": confidence,
        "provenance_links": provenance_links,
    }

    if logger is not None:
        log_transformation(
            logger,
            "formula_built",
            {
                "shade_ref": shade_ref,
                "shade_code": shade["shade_code"],
                "brand": shade["brand"],
                "line": shade["product_line"],
                "developer": developer_selection["developer"],
            },
        )

    if intake is not None:
        from hair_color_db.stage13_formulation_rules.resolver import resolve_formulation_rules
        from src.sub_range_intake import merge_intake_sub_ranges

        stage13_intake = merge_intake_sub_ranges(intake, shade_sub_range=shade.get("sub_range"))
        assert stage13_intake is not None
        stage13_intake.setdefault("gray_percentage", gray_percent or 0)
        if natural_level is not None:
            stage13_intake.setdefault("natural_level", int(natural_level))
        if existing_level is not None:
            stage13_intake.setdefault("existing_level", int(existing_level))
        if desired_level is not None:
            stage13_intake.setdefault("desired_level", int(desired_level))
        stage13_result = resolve_formulation_rules(
            stage13_intake,
            canonical_key=str(shade["canonical_key"]),
        )
        formula["formulation_rules"] = stage13_result.to_dict()

        if stage13_result.recommendation_status == "blocked":
            formula["status"] = "blocked"
        elif stage13_result.recommendation_status == "requires_consultation":
            formula["status"] = "requires_consultation"
        elif stage13_result.recommendation_status == "caution":
            formula["status"] = "caution"

        apply_stage13_formulation_overlay(
            formula,
            stage13_result,
            developer_options=developer_options if isinstance(developer_options, list) else None,
            heuristic_developer=developer_selection["developer"],
        )

        if stage13_result.fill_pigment_guidance:
            from src.fill_shade_lookup import enrich_fill_guidance_with_inventory

            formula["formula"]["fill_pigment_guidance"] = enrich_fill_guidance_with_inventory(
                conn,
                str(shade["canonical_key"]),
                stage13_result.fill_pigment_guidance,
            )

        formula["warnings"] = list(formula.get("warnings", [])) + stage13_result.warnings
        if stage13_result.block_reason:
            formula["block_reason"] = stage13_result.block_reason

        if logger is not None and stage13_result.developer_volume is not None:
            log_transformation(
                logger,
                "stage13_developer_applied",
                {
                    "shade_ref": shade_ref,
                    "developer_volume": stage13_result.developer_volume,
                    "developer": formula["formula"]["developer"],
                    "matched_rules": stage13_result.matched_rules,
                },
            )

    return formula
