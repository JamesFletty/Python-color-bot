"""v2 initial schema — simplified catalog + rules."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "v2_001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("brand_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand_name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("brand_id"),
        sa.UniqueConstraint("brand_name"),
    )
    op.create_table(
        "product_lines",
        sa.Column("line_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("line_name", sa.Text(), nullable=False),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("color_type", sa.Text(), nullable=True),
        sa.Column("mixing_ratio_default", sa.Text(), nullable=True),
        sa.Column("region_or_market", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.brand_id"]),
        sa.PrimaryKeyConstraint("line_id"),
        sa.UniqueConstraint("brand_id", "line_name", name="uq_product_lines_brand_line_name"),
        sa.UniqueConstraint("canonical_key"),
    )
    op.create_table(
        "shades",
        sa.Column("shade_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=False),
        sa.Column("shade_code", sa.Text(), nullable=False),
        sa.Column("shade_name", sa.Text(), nullable=True),
        sa.Column("level", sa.Numeric(3, 1), nullable=True),
        sa.Column("color_type", sa.Text(), nullable=True),
        sa.Column("sub_range", sa.Text(), nullable=True),
        sa.Column("mixing_ratio", sa.Text(), nullable=True),
        sa.Column("discontinued", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("gray_coverage_claim", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["line_id"], ["product_lines.line_id"]),
        sa.PrimaryKeyConstraint("shade_id"),
        sa.UniqueConstraint(
            "line_id", "shade_code", "sub_range", name="uq_shades_line_code_subrange"
        ),
    )
    op.create_table(
        "shade_tones",
        sa.Column("shade_id", sa.Integer(), nullable=False),
        sa.Column("tone_name", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["shade_id"], ["shades.shade_id"]),
        sa.PrimaryKeyConstraint("shade_id", "tone_name"),
    )
    op.create_table(
        "formulation_rules",
        sa.Column("rule_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("package_rule_id", sa.Text(), nullable=False),
        sa.Column("line_id", sa.Integer(), nullable=True),
        sa.Column("scope_level", sa.Text(), server_default=sa.text("'universal'"), nullable=False),
        sa.Column("sub_range", sa.Text(), nullable=True),
        sa.Column("rule_name", sa.Text(), nullable=False),
        sa.Column("rule_priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("rule_category", sa.Text(), nullable=False),
        sa.Column("evidence_status", sa.Text(), nullable=True),
        sa.Column("rule_condition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_dormant", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("warnings", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["line_id"], ["product_lines.line_id"]),
        sa.PrimaryKeyConstraint("rule_id"),
        sa.UniqueConstraint("package_rule_id"),
    )
    op.create_table(
        "cross_line_mappings",
        sa.Column("mapping_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversion_id", sa.Text(), nullable=False),
        sa.Column("source_line_id", sa.Integer(), nullable=False),
        sa.Column("source_shade_code", sa.Text(), nullable=False),
        sa.Column("target_line_id", sa.Integer(), nullable=False),
        sa.Column("target_shade_code", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Text(), server_default=sa.text("'exact'"), nullable=False),
        sa.Column("component_role", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_document", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_line_id"], ["product_lines.line_id"]),
        sa.ForeignKeyConstraint(["target_line_id"], ["product_lines.line_id"]),
        sa.PrimaryKeyConstraint("mapping_id"),
        sa.UniqueConstraint("conversion_id"),
        sa.UniqueConstraint(
            "source_line_id",
            "source_shade_code",
            "target_line_id",
            "component_role",
            name="uq_cross_line_source_target_role",
        ),
    )
    op.create_table(
        "consultations",
        sa.Column("consultation_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("shade_id", sa.Integer(), nullable=True),
        sa.Column("formula_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["shade_id"], ["shades.shade_id"]),
        sa.PrimaryKeyConstraint("consultation_id"),
    )


def downgrade() -> None:
    op.drop_table("consultations")
    op.drop_table("cross_line_mappings")
    op.drop_table("formulation_rules")
    op.drop_table("shade_tones")
    op.drop_table("shades")
    op.drop_table("product_lines")
    op.drop_table("brands")
