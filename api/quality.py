"""Formula response diagnostics shared by API and UI."""

from __future__ import annotations

from typing import Any


_CAUTION_STATUSES = {"caution", "requires_consultation", "blocked"}


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _formula_block(formula: dict[str, Any]) -> dict[str, Any]:
    block = formula.get("formula")
    return block if isinstance(block, dict) else formula


def build_quality_flags(
    formula: dict[str, Any],
    *,
    structured_request: dict[str, Any] | None = None,
    translation_notes: str | None = None,
) -> dict[str, Any]:
    """Summarize response quality concerns in a stable, UI-friendly shape."""
    block = _formula_block(formula)
    structured_request = structured_request or {}
    flags: dict[str, Any] = {
        "missing_processing_time": not _present(block.get("processing_time") or formula.get("processing_time")),
        "missing_gray_rule": False,
        "fallback_shade_used": bool(
            structured_request.get("grounding_note")
            or structured_request.get("_grounding_failed")
            or (translation_notes and "[Engine grounding]" in translation_notes)
        ),
        "low_confidence_catalog_match": str(formula.get("confidence", "")).lower() in {"low", "unresolved"},
        "stage13_status": formula.get("status") or formula.get("recommendation_status"),
        "blocked_or_caution": False,
        "warnings_present": bool(formula.get("warnings") or formula.get("risk_assessments")),
        "assumptions_present": bool(formula.get("assumptions")),
    }

    gray_value = None
    hair = formula.get("hair_conditions") if isinstance(formula.get("hair_conditions"), dict) else {}
    for candidate in (
        hair.get("gray_percent") if isinstance(hair, dict) else None,
        formula.get("gray_percentage"),
        structured_request.get("gray"),
    ):
        if candidate is not None:
            gray_value = candidate
            break
    try:
        has_gray = float(gray_value or 0) > 0
    except (TypeError, ValueError):
        has_gray = False
    if has_gray:
        flags["missing_gray_rule"] = not _present(
            block.get("gray_coverage_guidance")
            or formula.get("gray_coverage_guidance")
            or block.get("natural_shade_ratio")
            or formula.get("natural_shade_ratio")
        )

    status = str(flags["stage13_status"] or "").lower()
    flags["blocked_or_caution"] = status in _CAUTION_STATUSES
    active = [key for key, value in flags.items() if isinstance(value, bool) and value]
    flags["active"] = active
    flags["severity"] = "blocked" if status == "blocked" else "caution" if active else "ok"
    return flags


def build_rule_provenance_summary(formula: dict[str, Any]) -> dict[str, Any]:
    """Build compact 'why this formula' details for clients without raw JSON spelunking."""
    block = _formula_block(formula)
    shade = formula.get("shade") if isinstance(formula.get("shade"), dict) else {}
    rules = formula.get("formulation_rules") if isinstance(formula.get("formulation_rules"), dict) else {}
    hair = formula.get("hair_conditions") if isinstance(formula.get("hair_conditions"), dict) else {}
    return {
        "selected_shade_source": {
            "shade_code": shade.get("shade_code") or formula.get("shade_code"),
            "shade_name": shade.get("shade_name") or formula.get("shade_name"),
            "brand": shade.get("brand") or formula.get("brand"),
            "product_line": shade.get("product_line") or formula.get("line"),
            "confidence": formula.get("confidence"),
        },
        "matched_stage13_rules": rules.get("matched_rules") or formula.get("matched_rules") or [],
        "developer_source": {
            "developer": block.get("developer") or formula.get("developer_volume"),
            "developer_volume": rules.get("developer_volume") or formula.get("developer_volume"),
            "rationale": block.get("developer_rationale") or formula.get("developer_rationale") or [],
        },
        "processing_time_source": {
            "processing_time": block.get("processing_time") or formula.get("processing_time"),
        },
        "gray_rule_source": {
            "gray_percent": hair.get("gray_percent") or formula.get("gray_percentage"),
            "guidance": block.get("gray_coverage_guidance") or formula.get("gray_coverage_guidance"),
            "natural_shade_ratio": block.get("natural_shade_ratio") or formula.get("natural_shade_ratio"),
        },
        "data_gaps": formula.get("data_gaps") or [],
        "assumptions": formula.get("assumptions") or [],
        "warnings": formula.get("warnings") or [],
    }


def attach_diagnostics(
    formula: dict[str, Any],
    *,
    structured_request: dict[str, Any] | None = None,
    translation_notes: str | None = None,
) -> dict[str, Any]:
    """Return formula with response-level diagnostics attached."""
    formula["quality_flags"] = build_quality_flags(
        formula,
        structured_request=structured_request,
        translation_notes=translation_notes,
    )
    formula["rule_provenance"] = build_rule_provenance_summary(formula)
    return formula
