"""Stage 13 package validation (schema, enums, cross-references)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .loaders import (
    all_rule_ids,
    load_conflicts_and_gaps,
    load_line_overrides,
    load_manifest,
    load_ontology,
    load_service_workflows,
    load_universal_rules,
    load_validation_cases,
    stage12_canonical_keys_with_shades,
)
from .paths import ARTIFACT_FILES


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    location: str = ""


@dataclass
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str, location: str = "") -> None:
        self.issues.append(ValidationIssue(severity, code, message, location))
        if severity == "error":
            self.ok = False


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_artifact_files_exist(report: ValidationReport) -> None:
    """Ensure all section files from MANIFEST exist."""
    manifest = load_manifest()
    for section, filename in manifest.get("sections", {}).items():
        path = ARTIFACT_FILES["MANIFEST"].parent / filename
        if not path.exists():
            report.add("error", "missing_artifact", f"Missing section {section}: {filename}", str(path))


def validate_manifest_counts(report: ValidationReport) -> None:
    """Compare MANIFEST counts to loaded artifacts."""
    manifest = load_manifest()
    counts = manifest.get("counts", {})
    checks = {
        "universal_rules": len(load_universal_rules()),
        "service_workflows": len(load_service_workflows()),
        "brand_line_overrides": len(load_line_overrides()),
        "validation_cases": len(load_validation_cases()),
        "conflicts_and_gaps": len(load_conflicts_and_gaps()),
    }
    for key, actual in checks.items():
        expected = counts.get(key)
        if expected is not None and expected != actual:
            report.add(
                "error",
                "count_mismatch",
                f"MANIFEST counts.{key}={expected} but artifact has {actual}",
                "MANIFEST.json",
            )


def validate_rule_ids_unique(report: ValidationReport) -> None:
    """Every rule_id must be unique across universal + line overrides."""
    seen: dict[str, str] = {}
    for rule in load_universal_rules():
        rid = rule["rule_id"]
        if rid in seen:
            report.add("error", "duplicate_rule_id", f"Duplicate rule_id {rid}", "B")
        seen[rid] = "universal"
    for group in load_line_overrides():
        for rule in group.get("override_rules", []):
            rid = rule["rule_id"]
            if rid in seen:
                report.add(
                    "error",
                    "duplicate_rule_id",
                    f"Duplicate rule_id {rid} in {group['canonical_key']}",
                    "D",
                )
            seen[rid] = group["canonical_key"]


def validate_rule_shape(report: ValidationReport) -> None:
    """Validate rule_condition / rule_action structure on executable rules."""
    required_rule_fields = {"rule_id", "rule_priority", "rule_condition", "rule_action"}
    for rule in load_universal_rules():
        missing = required_rule_fields - set(rule)
        if missing:
            report.add(
                "error",
                "invalid_rule_shape",
                f"Universal rule {rule.get('rule_id')} missing {sorted(missing)}",
                "B",
            )
        condition = rule.get("rule_condition") or {}
        if not condition.get("all_of") and not condition.get("any_of"):
            report.add(
                "warning",
                "empty_rule_condition",
                f"Rule {rule.get('rule_id')} has no predicates",
                "B",
            )


def validate_validation_case_references(report: ValidationReport) -> None:
    """Validation cases must reference known rule IDs when listed."""
    known = all_rule_ids()
    for case in load_validation_cases():
        case_id = case.get("case_id", "?")
        expected = case.get("expected", {})
        for rule_id in expected.get("matched_rules", []):
            if rule_id not in known:
                report.add(
                    "error",
                    "unknown_rule_reference",
                    f"Case {case_id} references unknown rule_id {rule_id}",
                    "F",
                )


def validate_dormant_override_flags(report: ValidationReport) -> None:
    """Dormant groups must not have Stage 12 shade inventory yet."""
    shade_keys = stage12_canonical_keys_with_shades()
    dormant_expected = {
        "Matrix::Coil Color::US",
        "Matrix::Super Sync::US",
        "Matrix::Tonal Control::US",
    }
    for group in load_line_overrides():
        if group.get("requires_stage12_inventory_addition"):
            key = group["canonical_key"]
            if key in shade_keys:
                report.add(
                    "warning",
                    "dormant_line_has_inventory",
                    f"{key} marked dormant but has Stage 12 shades — consider clearing flag",
                    "D",
                )
            elif key not in dormant_expected:
                report.add(
                    "warning",
                    "unexpected_dormant_line",
                    f"{key} requires_stage12_inventory_addition=true",
                    "D",
                )


def validate_service_intents_in_ontology(report: ValidationReport) -> None:
    """Service intents used in validation cases should exist in ontology enums."""
    ontology = load_ontology()
    service_intents = set(ontology.get("enums", {}).get("service_intent", []))
    if not service_intents:
        return
    for case in load_validation_cases():
        intent = case.get("input", {}).get("service_intent")
        if intent and intent not in service_intents:
            report.add(
                "warning",
                "unknown_service_intent",
                f"Case {case.get('case_id')} uses service_intent={intent!r} not in ontology",
                "F",
            )


def validate_package() -> ValidationReport:
    """Run all Stage 13 package validators."""
    report = ValidationReport(ok=True)
    validate_artifact_files_exist(report)
    validate_manifest_counts(report)
    validate_rule_ids_unique(report)
    validate_rule_shape(report)
    validate_validation_case_references(report)
    validate_dormant_override_flags(report)
    validate_service_intents_in_ontology(report)
    return report


def format_report(report: ValidationReport) -> str:
    """Format validation report for CLI output."""
    lines = [f"status: {'ok' if report.ok else 'failed'}", f"issues: {len(report.issues)}"]
    for issue in report.issues:
        loc = f" ({issue.location})" if issue.location else ""
        lines.append(f"  [{issue.severity}] {issue.code}{loc}: {issue.message}")
    return "\n".join(lines)
