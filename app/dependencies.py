"""Database session dependency (Phase 2 — wired after Alembic + seed_db)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session once engine wiring lands in Phase 2."""
    raise NotImplementedError("Database session wiring is Phase 2 work.")
