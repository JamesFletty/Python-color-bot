"""Alembic revision: Stage 13 formulation rule import schema extensions.

Revision ID: op002_stage13_import
Revises: op001_production_layer
Create Date: 2026-06-16

Adds columns and tables required by H_schema_extension_proposal.json so Stage 13
JSON rules can load into PostgreSQL deterministically via import_stage13_rules.py.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "op002_stage13_import"
down_revision: Union[str, None] = "op001_production_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGE13_RULE_CATEGORIES = (
    "safety",
    "color_science",
    "product_type",
    "application",
    "intermixing",
)


def upgrade() -> None:
    for value in _STAGE13_RULE_CATEGORIES:
        op.execute(
            f"ALTER TYPE formulation_rule_category ADD VALUE IF NOT EXISTS '{value}'"
        )

    op.add_column(
        "formulation_rule",
        sa.Column("package_rule_id", sa.String(), nullable=True),
    )
    op.add_column(
        "formulation_rule",
        sa.Column(
            "scope_level",
            sa.String(),
            nullable=False,
            server_default="universal",
        ),
    )
    op.add_column(
        "formulation_rule",
        sa.Column("canonical_key", sa.String(), nullable=True),
    )
    op.add_column(
        "formulation_rule",
        sa.Column(
            "is_dormant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "idx_formulation_rule_package_rule_id",
        "formulation_rule",
        ["package_rule_id"],
        unique=True,
    )

    op.create_table(
        "service_workflow",
        sa.Column("workflow_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("service_intent", sa.String(), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "default_zones",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "applicable_line_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
    )

    op.create_table(
        "validation_case",
        sa.Column("case_id", sa.String(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.String(), nullable=True),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expected", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(), nullable=True),
    )

    op.create_table(
        "formulation_rule_evidence",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_document.source_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("evidence_status", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("formulation_rule_evidence")
    op.drop_table("validation_case")
    op.drop_table("service_workflow")
    op.drop_index("idx_formulation_rule_package_rule_id", table_name="formulation_rule")
    op.drop_column("formulation_rule", "is_dormant")
    op.drop_column("formulation_rule", "canonical_key")
    op.drop_column("formulation_rule", "scope_level")
    op.drop_column("formulation_rule", "package_rule_id")
