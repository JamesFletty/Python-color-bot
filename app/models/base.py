"""SQLAlchemy declarative base for v2."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for v2 operational models."""
