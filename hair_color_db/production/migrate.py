"""Apply PostgreSQL schema migrations from packaged SQL files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from .db import create_db_engine, resolve_database_url

_PRODUCTION_DIR = Path(__file__).resolve().parent

# A PostgreSQL dollar-quote tag: ``$$`` or ``$identifier$``.
_DOLLAR_QUOTE_TAG = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")

MIGRATIONS: tuple[tuple[str, Path], ...] = (
    ("research_baseline", _PRODUCTION_DIR / "research_baseline_schema.sql"),
    ("op001_production_layer", _PRODUCTION_DIR / "production_operational_schema.sql"),
)


def _statements(sql: str) -> list[str]:
    """Split a SQL script into individual statements.

    Splits on ``;`` only at the top level. Single-quoted string literals and
    PostgreSQL dollar-quoted bodies (``$$ ... ; ... $$`` / ``$tag$ ... $tag$``)
    are treated as opaque so semicolons inside them do not split a statement.
    Line (``-- ...``) and block (``/* ... */``) comments are stripped.
    """
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_single = False
    dollar_tag: str | None = None

    def flush() -> None:
        statement = "".join(buf).strip()
        if statement:
            statements.append(statement)
        buf.clear()

    while i < n:
        ch = sql[i]

        if dollar_tag is not None:
            if sql.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
            else:
                buf.append(ch)
                i += 1
            continue

        if in_single:
            buf.append(ch)
            i += 1
            if ch == "'":
                if i < n and sql[i] == "'":  # escaped '' inside a string literal
                    buf.append("'")
                    i += 1
                else:
                    in_single = False
            continue

        if sql.startswith("--", i):
            newline = sql.find("\n", i)
            i = n if newline == -1 else newline
            continue

        if sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = n if end == -1 else end + 2
            buf.append(" ")
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == "$":
            match = _DOLLAR_QUOTE_TAG.match(sql, i)
            if match:
                dollar_tag = match.group(0)
                buf.append(dollar_tag)
                i += len(dollar_tag)
                continue

        if ch == ";":
            flush()
            i += 1
            continue

        buf.append(ch)
        i += 1

    flush()
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
    """Apply all pending migrations in order. Returns newly applied revision ids."""
    db_engine = engine or create_db_engine(database_url)
    applied_now: list[str] = []
    with db_engine.begin() as connection:
        for revision_id, sql_path in MIGRATIONS:
            if apply_migration(connection, revision_id, sql_path):
                applied_now.append(revision_id)
    return applied_now


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
