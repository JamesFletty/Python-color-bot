"""Bootstrap PostgreSQL: migrate schema and import Stage 12 + Stage 13 data."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .db import create_db_engine, resolve_database_url
from .import_stage12_research import import_stage12_research, validate_import_counts
from .import_stage13_rules import SqlAlchemyCanonicalKeyResolver, import_stage13_rules
from .migrate import apply_pending_migrations


@dataclass(frozen=True)
class BootstrapSummary:
    migrations_applied: list[str]
    stage12: dict[str, object]
    stage12_report: dict[str, object]
    stage13: dict[str, object]


def bootstrap_database(
    session: Session,
    *,
    engine: Engine | None = None,
    database_url: str | None = None,
    skip_migrate: bool = False,
    skip_stage12: bool = False,
    skip_stage13: bool = False,
) -> BootstrapSummary:
    """
    End-to-end PostgreSQL bootstrap for local dev and integration tests.

    Order: schema migrations → Stage 12 research import → Stage 13 rules import.
    """
    migrations_applied: list[str] = []
    if not skip_migrate:
        db_engine = engine or session.get_bind()
        if not isinstance(db_engine, Engine):
            db_engine = create_db_engine(database_url)
        migrations_applied = apply_pending_migrations(db_engine)

    stage12_summary: dict[str, object] = {}
    stage12_report: dict[str, object] = {}
    if not skip_stage12:
        result = import_stage12_research(session)
        stage12_summary = {
            "shades": result.shades,
            "tone_mappings": result.tone_mappings,
            "line_technical_rules": result.line_technical_rules,
            "intermixing_rules": result.intermixing_rules,
        }
        stage12_report = validate_import_counts(
            session, tone_mappings_imported=result.tone_mappings
        )

    stage13_summary: dict[str, object] = {}
    if not skip_stage13:
        resolver = SqlAlchemyCanonicalKeyResolver(session)
        result = import_stage13_rules(session, resolver=resolver)
        stage13_summary = {
            "universal_rules": result.universal_rules,
            "line_rules": result.line_rules,
            "dormant_line_rules": result.dormant_line_rules,
            "service_workflows": result.service_workflows,
            "validation_cases": result.validation_cases,
        }

    return BootstrapSummary(
        migrations_applied=migrations_applied,
        stage12=stage12_summary,
        stage12_report=stage12_report,
        stage13=stage13_summary,
    )


def bootstrap_from_env(database_url: str | None = None) -> BootstrapSummary:
    """Open a session from ``DATABASE_URL``, bootstrap, and commit."""
    from .db import create_session_factory

    url = resolve_database_url(database_url)
    engine = create_db_engine(url)
    SessionLocal = create_session_factory(engine)
    with SessionLocal() as session:
        summary = bootstrap_database(session, engine=engine)
        session.commit()
        return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import os
    import sys

    from .db import require_database_url

    parser = argparse.ArgumentParser(
        description="Bootstrap PostgreSQL schema and import Stage 12 + Stage 13 packages"
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    parser.add_argument("--skip-migrate", action="store_true")
    parser.add_argument("--skip-stage12", action="store_true")
    parser.add_argument("--skip-stage13", action="store_true")
    args = parser.parse_args(argv)

    if not require_database_url(args.database_url):
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    summary = bootstrap_from_env(args.database_url)
    print(
        json.dumps(
            {
                "migrations_applied": summary.migrations_applied,
                "stage12": summary.stage12,
                "stage12_report": summary.stage12_report,
                "stage13": summary.stage13,
                "status": "ok",
            },
            indent=2,
        )
    )
    if summary.stage12_report and not (
        summary.stage12_report.get("shade_count_ok", True)
        and summary.stage12_report.get("tone_mapping_count_ok", True)
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
