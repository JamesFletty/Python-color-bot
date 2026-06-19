"""production operational schema

Revision ID: op001_production_layer
Revises: research_baseline
Create Date: 2026-06-19
"""

from __future__ import annotations

from pathlib import Path

from alembic import op
from sqlalchemy import text

from hair_color_db.production.migrate import _statements

revision = "op001_production_layer"
down_revision = "research_baseline"
branch_labels = None
depends_on = None


def _sql_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "hair_color_db" / "production" / filename


def upgrade() -> None:
    bind = op.get_bind()
    sql = _sql_path("production_operational_schema.sql").read_text(encoding="utf-8")
    for statement in _statements(sql):
        bind.execute(text(statement + ";"))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the production operational schema")
