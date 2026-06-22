"""Import Stage 13 formulation rules into production PostgreSQL tables.

Reads B_universal_rule_library.json, D_brand_line_overrides.json,
C_service_workflows.json, and F_validation_cases.json; upserts rows into
formulation_rule (+ join tables), service_workflow, and validation_case.

Idempotent: re-running with the same package updates rows keyed by
package_rule_id / workflow_id / case_id without duplicating.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hair_color_db.stage13_formulation_rules.loaders import (
    load_line_overrides,
    load_service_workflows,
    load_universal_rules,
    load_validation_cases,
    stage12_canonical_keys_with_shades,
)

from .production_models import (
    FormulationRule,
    FormulationRuleBrand,
    FormulationRuleCategory,
    FormulationRuleEvidence,
    FormulationRuleLine,
    IntermixEvidenceStatus,
    ServiceWorkflow,
    ValidationCase,
)

STAGE13_RULE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

_STAGE13_RULE_CATEGORIES = (
    "deposit",
    "developer_selection",
)


def _ensure_stage13_rule_categories(session: Session) -> None:
    """Extend formulation_rule_category for Stage 13 values missing from older schemas."""
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    for value in _STAGE13_RULE_CATEGORIES:
        session.execute(
            text(
                f"ALTER TYPE formulation_rule_category "
                f"ADD VALUE IF NOT EXISTS '{value}'"
            )
        )


@dataclass(frozen=True)
class LineScope:
    """Resolved brand/line applicability for a canonical key."""

    brand_id: uuid.UUID | None = None
    line_id: uuid.UUID | None = None


@dataclass
class Stage13RuleImportRow:
    """Normalized row ready for persistence."""

    package_rule_id: str
    rule_id: uuid.UUID
    rule_name: str
    rule_priority: int
    rule_condition: dict[str, Any]
    rule_action: dict[str, Any]
    rule_category: str
    evidence_status: str
    scope_level: str
    canonical_key: str | None = None
    is_dormant: bool = False
    is_active: bool = True
    test_coverage: bool = False
    brand_id: uuid.UUID | None = None
    line_id: uuid.UUID | None = None


@dataclass
class Stage13ImportSummary:
    universal_rules: int = 0
    line_rules: int = 0
    dormant_line_rules: int = 0
    service_workflows: int = 0
    validation_cases: int = 0


class CanonicalKeyResolver(Protocol):
    """Resolve canonical_key strings to production brand/line UUIDs."""

    def resolve(self, canonical_key: str) -> LineScope: ...


def parse_canonical_key(canonical_key: str) -> tuple[str, str, str]:
    """Split ``Brand::Line::Region`` canonical keys."""
    parts = canonical_key.split("::")
    if len(parts) != 3:
        raise ValueError(f"Invalid canonical_key format: {canonical_key!r}")
    return parts[0], parts[1], parts[2]


def deterministic_rule_id(package_rule_id: str) -> uuid.UUID:
    """Stable UUID for a Stage 13 package rule id (U001, M_SOCOLOR_001, …)."""
    return uuid.uuid5(STAGE13_RULE_NAMESPACE, package_rule_id)


def _validation_case_rule_ids() -> set[str]:
    ids: set[str] = set()
    for case in load_validation_cases():
        for rule_id in case.get("expected", {}).get("matched_rules", []):
            ids.add(str(rule_id))
    return ids


def _is_dormant_group(canonical_key: str, requires_inventory: bool) -> bool:
    if not requires_inventory:
        return False
    return canonical_key not in stage12_canonical_keys_with_shades()


def build_stage13_import_rows(
    resolver: CanonicalKeyResolver | None = None,
) -> list[Stage13RuleImportRow]:
    """Build import rows from Stage 13 JSON artifacts."""
    covered_rule_ids = _validation_case_rule_ids()
    rows: list[Stage13RuleImportRow] = []

    for rule in load_universal_rules():
        package_rule_id = str(rule["rule_id"])
        rows.append(
            Stage13RuleImportRow(
                package_rule_id=package_rule_id,
                rule_id=deterministic_rule_id(package_rule_id),
                rule_name=str(rule["rule_name"]),
                rule_priority=int(rule.get("rule_priority", 100)),
                rule_condition=dict(rule.get("rule_condition", {})),
                rule_action=dict(rule.get("rule_action", {})),
                rule_category=str(rule["rule_category"]),
                evidence_status=str(rule.get("evidence_status", "inferred")),
                scope_level="universal",
                test_coverage=package_rule_id in covered_rule_ids,
            )
        )

    for group in load_line_overrides():
        canonical_key = str(group["canonical_key"])
        requires_inventory = bool(group.get("requires_stage12_inventory_addition"))
        is_dormant = _is_dormant_group(canonical_key, requires_inventory)
        scope = resolver.resolve(canonical_key) if resolver else LineScope()

        for rule in group.get("override_rules", []):
            package_rule_id = str(rule["rule_id"])
            rows.append(
                Stage13RuleImportRow(
                    package_rule_id=package_rule_id,
                    rule_id=deterministic_rule_id(package_rule_id),
                    rule_name=str(rule["rule_name"]),
                    rule_priority=int(rule.get("rule_priority", 100)),
                    rule_condition=dict(rule.get("rule_condition", {})),
                    rule_action=dict(rule.get("rule_action", {})),
                    rule_category=str(rule["rule_category"]),
                    evidence_status=str(rule.get("evidence_status", "inferred")),
                    scope_level="line",
                    canonical_key=canonical_key,
                    is_dormant=is_dormant,
                    is_active=not is_dormant,
                    test_coverage=package_rule_id in covered_rule_ids,
                    brand_id=scope.brand_id,
                    line_id=scope.line_id,
                )
            )

    return rows


def import_rows_to_formulation_rule_records(
    rows: list[Stage13RuleImportRow],
) -> list[Any]:
    """Convert import rows to in-memory engine records (active rules only)."""
    from .repositories import FormulationRuleRecord

    records: list[FormulationRuleRecord] = []
    for row in rows:
        if not row.is_active:
            continue
        if row.scope_level == "line" and not row.line_id:
            continue
        brand_ids = [row.brand_id] if row.brand_id else []
        line_ids = [row.line_id] if row.line_id else []
        records.append(
            FormulationRuleRecord(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                rule_priority=row.rule_priority,
                rule_condition=row.rule_condition,
                rule_action=row.rule_action,
                rule_category=row.rule_category,
                brand_ids=brand_ids,
                line_ids=line_ids,
                scope_level=row.scope_level,
            )
        )
    return records


def _evidence_status(value: str) -> IntermixEvidenceStatus:
    try:
        return IntermixEvidenceStatus(value)
    except ValueError:
        return IntermixEvidenceStatus.INFERRED


def _rule_category(value: str) -> FormulationRuleCategory:
    return FormulationRuleCategory(value)


def import_stage13_rules(
    session: Session,
    resolver: CanonicalKeyResolver | None = None,
) -> Stage13ImportSummary:
    """Upsert Stage 13 package artifacts into PostgreSQL (idempotent)."""
    summary = Stage13ImportSummary()
    _ensure_stage13_rule_categories(session)
    rule_rows = build_stage13_import_rows(resolver=resolver)

    # Migration SQL may seed legacy rules without package_rule_id; remove before upsert.
    legacy_names = [row.rule_name for row in rule_rows]
    session.execute(
        delete(FormulationRule).where(
            FormulationRule.rule_name.in_(legacy_names),
            FormulationRule.package_rule_id.is_(None),
        )
    )

    for row in rule_rows:
        if row.scope_level == "universal":
            summary.universal_rules += 1
        else:
            summary.line_rules += 1
            if row.is_dormant:
                summary.dormant_line_rules += 1

        stmt = (
            insert(FormulationRule)
            .values(
                rule_id=row.rule_id,
                rule_name=row.rule_name,
                rule_priority=row.rule_priority,
                rule_condition=row.rule_condition,
                rule_action=row.rule_action,
                rule_category=_rule_category(row.rule_category),
                is_active=row.is_active,
                evidence_status=_evidence_status(row.evidence_status),
                test_coverage=row.test_coverage,
                package_rule_id=row.package_rule_id,
                scope_level=row.scope_level,
                canonical_key=row.canonical_key,
                is_dormant=row.is_dormant,
            )
            .on_conflict_do_update(
                index_elements=[FormulationRule.package_rule_id],
                set_={
                    "rule_name": row.rule_name,
                    "rule_priority": row.rule_priority,
                    "rule_condition": row.rule_condition,
                    "rule_action": row.rule_action,
                    "rule_category": _rule_category(row.rule_category),
                    "is_active": row.is_active,
                    "evidence_status": _evidence_status(row.evidence_status),
                    "test_coverage": row.test_coverage,
                    "scope_level": row.scope_level,
                    "canonical_key": row.canonical_key,
                    "is_dormant": row.is_dormant,
                },
            )
        )
        session.execute(stmt)

        session.execute(
            delete(FormulationRuleBrand).where(FormulationRuleBrand.rule_id == row.rule_id)
        )
        session.execute(
            delete(FormulationRuleLine).where(FormulationRuleLine.rule_id == row.rule_id)
        )

        if row.brand_id:
            session.merge(
                FormulationRuleBrand(rule_id=row.rule_id, brand_id=row.brand_id)
            )
        if row.line_id:
            session.merge(
                FormulationRuleLine(rule_id=row.rule_id, line_id=row.line_id)
            )

        session.merge(
            FormulationRuleEvidence(
                rule_id=row.rule_id,
                source_id=None,
                evidence_status=row.evidence_status,
                notes=f"Imported from Stage 13 package ({row.package_rule_id})",
            )
        )

    for workflow in load_service_workflows():
        session.merge(
            ServiceWorkflow(
                workflow_id=str(workflow["workflow_id"]),
                name=str(workflow["name"]),
                service_intent=str(workflow["service_intent"]),
                steps=list(workflow.get("steps", [])),
                default_zones=list(workflow.get("default_zones", [])),
                applicable_line_categories=list(
                    workflow.get("applicable_line_categories", [])
                ),
            )
        )
        summary.service_workflows += 1

    for case in load_validation_cases():
        session.merge(
            ValidationCase(
                case_id=str(case["case_id"]),
                description=str(case.get("description", "")),
                canonical_key=case.get("canonical_key"),
                input=dict(case.get("input", {})),
                expected=dict(case.get("expected", {})),
            )
        )
        summary.validation_cases += 1

    session.flush()
    return summary


class SqlAlchemyCanonicalKeyResolver:
    """Resolve canonical keys via brand / product_line / product_line_region joins."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._cache: dict[str, LineScope] = {}

    def resolve(self, canonical_key: str) -> LineScope:
        if canonical_key in self._cache:
            return self._cache[canonical_key]

        from .production_models import Brand, ProductLine, ProductLineRegion

        brand_name, line_name, region = parse_canonical_key(canonical_key)
        row = self.session.execute(
            select(ProductLine.line_id, ProductLine.brand_id)
            .join(Brand, Brand.brand_id == ProductLine.brand_id)
            .join(ProductLineRegion, ProductLineRegion.line_id == ProductLine.line_id)
            .where(
                Brand.brand_name == brand_name,
                ProductLine.product_line_name == line_name,
                ProductLineRegion.region_or_market == region,
            )
            .limit(1)
        ).first()

        scope = LineScope(
            brand_id=row.brand_id if row else None,
            line_id=row.line_id if row else None,
        )
        self._cache[canonical_key] = scope
        return scope


@dataclass
class DictCanonicalKeyResolver:
    """In-memory resolver keyed by canonical_key for tests and seed repos."""

    mapping: dict[str, LineScope] = field(default_factory=dict)

    def resolve(self, canonical_key: str) -> LineScope:
        return self.mapping.get(canonical_key, LineScope())


def build_formulation_rules_from_stage13(
    *,
    line_mapping: dict[str, LineScope] | None = None,
    resolver: CanonicalKeyResolver | None = None,
) -> list[Any]:
    """Load active formulation rules from the Stage 13 JSON package."""
    key_resolver = resolver
    if key_resolver is None and line_mapping is not None:
        key_resolver = DictCanonicalKeyResolver(mapping=line_mapping)
    rows = build_stage13_import_rows(resolver=key_resolver)
    return import_rows_to_formulation_rule_records(rows)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: import Stage 13 rules into a PostgreSQL database."""
    import argparse
    import os
    import sys

    from .db import create_session_factory, require_database_url

    parser = argparse.ArgumentParser(description="Import Stage 13 rules into PostgreSQL")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    args = parser.parse_args(argv)

    if not require_database_url(args.database_url):
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    SessionLocal = create_session_factory(database_url=args.database_url)
    with SessionLocal() as session:
        resolver = SqlAlchemyCanonicalKeyResolver(session)
        summary = import_stage13_rules(session, resolver=resolver)
        session.commit()
        print(
            f"Imported {summary.universal_rules} universal + {summary.line_rules} line rules "
            f"({summary.dormant_line_rules} dormant), "
            f"{summary.service_workflows} workflows, "
            f"{summary.validation_cases} validation cases."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
