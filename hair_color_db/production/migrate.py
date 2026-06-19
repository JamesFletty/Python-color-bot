"""Apply PostgreSQL schema migrations from packaged SQL files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from .db import create_db_engine, resolve_database_url

_PRODUCTION_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PRODUCTION_DIR.parents[1]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"

MIGRATIONS: tuple[tuple[str, Path], ...] = (
    ("research_baseline", _PRODUCTION_DIR / "research_baseline_schema.sql"),
    ("op001_production_layer", _PRODUCTION_DIR / "production_operational_schema.sql"),
)


def _statements(sql: str) -> list[str]:
    """Split SQL migration text into executable statements.

    PostgreSQL migration files may contain semicolons inside single-quoted
    strings, double-quoted identifiers, comments, or dollar-quoted function
    bodies. A simple ``sql.split(";")`` corrupts dollar-quoted PL/pgSQL
    blocks, so this scanner only splits on top-level semicolons.
    """
    statements: list[str] = []
    current: list[str] = []
    index = 0
    quote: str | None = None
    dollar_tag: str | None = None
    line_comment = False
    block_comment = False

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
                current.append(char)
            index += 1
            continue

        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue

        if dollar_tag is not None:
            if sql.startswith(dollar_tag, index):
                current.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                current.append(char)
                index += 1
            continue

        if quote is not None:
            current.append(char)
            if char == quote:
                if next_char == quote:
                    current.append(next_char)
                    index += 2
                    continue
                quote = None
            index += 1
            continue

        if char == "-" and next_char == "-":
            line_comment = True
            index += 2
            continue

        if char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue

        if char in {"'", '"'}:
            quote = char
            current.append(char)
            index += 1
            continue

        if char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if match:
                dollar_tag = match.group(0)
                current.append(dollar_tag)
                index += len(dollar_tag)
                continue

        if char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def _ensure_migration_table(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migration (
                revision_id VARCHAR PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )


def _applied_revisions(connection: Connection) -> set[str]:
    _ensure_migration_table(connection)
    rows = connection.execute(text("SELECT revision_id FROM schema_migration")).fetchall()
    return {row[0] for row in rows}


def apply_migration(connection: Connection, revision_id: str, sql_path: Path) -> bool:
    """
    Apply one migration revision when not already recorded.

    Returns True when statements were executed, False when already applied.
    """
    applied = _applied_revisions(connection)
    if revision_id in applied:
        return False

    sql = sql_path.read_text(encoding="utf-8")
    for statement in _statements(sql):
        if statement.upper().startswith("CREATE EXTENSION"):
            connection.execute(text(statement + ";"))
            continue
        connection.execute(text(statement + ";"))

    connection.execute(
        text("INSERT INTO schema_migration (revision_id) VALUES (:revision_id)"),
        {"revision_id": revision_id},
    )
    return True


def apply_pending_migrations(
    engine: Engine | None = None,
    *,
    database_url: str | None = None,
) -> list[str]:
    """Apply all pending migrations through Alembic. Returns applied head revisions."""
    from alembic import command
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    db_engine = engine or create_db_engine(database_url)
    alembic_config = _alembic_config(database_url=database_url)
    head_revision = ScriptDirectory.from_config(alembic_config).get_current_head()

    with db_engine.connect() as connection:
        before = MigrationContext.configure(connection).get_current_revision()
        alembic_config.attributes["connection"] = connection
        command.upgrade(alembic_config, "head")
        after = MigrationContext.configure(connection).get_current_revision()

    if before == after:
        return []
    if before is None and after == head_revision:
        return [revision for revision, _ in MIGRATIONS]
    if before == MIGRATIONS[0][0] and after == head_revision:
        return [MIGRATIONS[1][0]]
    return [after or head_revision]


def _alembic_config(database_url: str | None = None) -> Any:
    """Build an Alembic config pointed at this repository's migration project."""
    from alembic.config import Config

    config = Config(str(_ALEMBIC_INI))
    config.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


@dataclass(frozen=True)
class MigrationSummary:
    applied: list[str]
    skipped: list[str]


def migrate_database(database_url: str | None = None) -> MigrationSummary:
    """CLI-friendly migration runner."""
    url = resolve_database_url(database_url)
    engine = create_db_engine(url)
    applied = apply_pending_migrations(engine)
    skipped = [revision for revision, _ in MIGRATIONS if revision not in applied]
    return MigrationSummary(applied=applied, skipped=skipped)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import os
    import sys

    from .db import require_database_url

    parser = argparse.ArgumentParser(description="Apply PostgreSQL schema migrations")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL)",
    )
    args = parser.parse_args(argv)

    if not require_database_url(args.database_url):
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 1

    summary = migrate_database(args.database_url)
    print(
        json.dumps(
            {
                "applied": summary.applied,
                "skipped": summary.skipped,
                "status": "ok",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
