"""Central PostgreSQL connection helpers (DATABASE_URL)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def resolve_database_url(database_url: str | None = None) -> str:
    """Return a PostgreSQL URL from argument or ``DATABASE_URL`` env."""
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL or --database-url is required")
    return url


def create_db_engine(database_url: str | None = None, **engine_kwargs: object) -> Engine:
    """Create a SQLAlchemy engine from ``DATABASE_URL`` or an explicit URL."""
    return create_engine(resolve_database_url(database_url), **engine_kwargs)


def create_session_factory(
    engine: Engine | None = None,
    *,
    database_url: str | None = None,
) -> sessionmaker[Session]:
    """Return a session factory bound to the given or newly created engine."""
    bound_engine = engine or create_db_engine(database_url)
    return sessionmaker(bind=bound_engine)


@contextmanager
def db_session(
    database_url: str | None = None,
    *,
    engine: Engine | None = None,
    commit: bool = False,
) -> Iterator[Session]:
    """
    Context manager yielding a SQLAlchemy session.

    Commits on exit when ``commit=True``; otherwise the caller must commit.
    Rolls back on exception.
    """
    SessionLocal = create_session_factory(engine=engine, database_url=database_url)
    session = SessionLocal()
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def require_database_url(database_url: str | None = None) -> str:
    """Like ``resolve_database_url`` but returns None-safe for CLI exit codes."""
    try:
        return resolve_database_url(database_url)
    except ValueError:
        return ""
