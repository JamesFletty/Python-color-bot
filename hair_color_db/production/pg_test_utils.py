"""Shared PostgreSQL test bootstrap helpers."""

from __future__ import annotations

import os
import unittest
from dataclasses import dataclass

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .bootstrap import BootstrapSummary, bootstrap_database
from .db import create_db_engine, create_session_factory


@dataclass(frozen=True)
class PostgreSqlTestContext:
    """Reusable PostgreSQL test context for unittest integration classes."""

    engine: Engine
    Session: sessionmaker[Session]
    bootstrap: BootstrapSummary


_SHARED_CONTEXT: PostgreSqlTestContext | None = None
_SHARED_DATABASE_URL: str | None = None


def get_postgres_test_context() -> PostgreSqlTestContext:
    """Bootstrap the configured PostgreSQL test database once per Python process."""
    global _SHARED_CONTEXT, _SHARED_DATABASE_URL

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise unittest.SkipTest("DATABASE_URL not set; PostgreSQL tests skipped")

    if _SHARED_CONTEXT is not None and _SHARED_DATABASE_URL == database_url:
        return _SHARED_CONTEXT

    engine = create_db_engine(database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        bootstrap = bootstrap_database(session, engine=engine)
        session.commit()

    _SHARED_CONTEXT = PostgreSqlTestContext(
        engine=engine,
        Session=session_factory,
        bootstrap=bootstrap,
    )
    _SHARED_DATABASE_URL = database_url
    return _SHARED_CONTEXT
