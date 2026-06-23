"""Add line technical defaults.

Revision ID: v2_002_line_technical_defaults
Revises: v2_001_initial_schema
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v2_002_line_technical_defaults"
down_revision = "v2_001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_lines", sa.Column("developer_default_volume", sa.Integer(), nullable=True))
    op.add_column("product_lines", sa.Column("processing_time_default_minutes", sa.Integer(), nullable=True))
    op.add_column(
        "product_lines",
        sa.Column("technical_defaults", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("product_lines", "technical_defaults")
    op.drop_column("product_lines", "processing_time_default_minutes")
    op.drop_column("product_lines", "developer_default_volume")
