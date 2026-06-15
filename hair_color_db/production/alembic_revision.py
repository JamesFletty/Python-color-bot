"""Alembic revision: operational schema extensions for the formula engine.

Revision ID: op001_production_layer
Revises: research_baseline
Create Date: 2026-06-12

Recognized rule_value JSON shapes for line_technical_rule backfill
------------------------------------------------------------------
rule_type = 'developer':
  - {"options": [...], "strengths": [{"volume": "20 Vol", "lift_levels": 2, ...}]}
  - {"collection_overrides": [{"volume": "20 Volume (6%)", ...}]}
  Volume parsed from first integer in volume string (10/20/30/40).
  max_lift_levels from strengths[].lift_levels when numeric.

rule_type = 'mixing_ratio':
  - {"default": "1:1 with ...", "variants": [{"ratio": "1:2", ...}]}
  Parses N:D from default or first variant ratio string.

rule_type = 'processing_time':
  - {"ranges": [{"min_minutes": 30, "max_minutes": 45, ...}]}
  Uses min_minutes when present.

rule_type = 'gray_coverage':
  - {"rules": ["50-100% grey hair: ...", "up to 100% coverage", ...]}
  Extracts leading percentage from first rule containing '%' when unambiguous.

rule_type = 'lift':
  - {"rules": [{"lift_levels": 3, "developer": "12%"}, ...]}
  Uses first numeric lift_levels value.

Ambiguous or non-matching JSON is skipped; rule_value is never modified.
"""

from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "op001_production_layer"
down_revision: Union[str, None] = "research_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum definitions
COLOR_SCIENCE_CONFIDENCE = postgresql.ENUM(
    "established", "debated", "inferred", name="color_science_confidence"
)
INTERMIX_RESTRICTION_TYPE = postgresql.ENUM(
    "not_mixable",
    "caution",
    "ratio_required",
    "developer_override",
    name="intermix_restriction_type",
)
INTERMIX_EVIDENCE_STATUS = postgresql.ENUM(
    "confirmed",
    "manufacturer_stated",
    "educator_reported",
    "inferred",
    name="intermix_evidence_status",
)
INTERMIX_RULE_SCOPE = postgresql.ENUM(
    "shade_pair",
    "sub_range_internal_only",
    "sub_range_isolated_from_line",
    "cross_sub_range",
    name="intermix_rule_scope",
)
FORMULATION_RULE_CATEGORY = postgresql.ENUM(
    "lift",
    "tone",
    "neutralization",
    "gray_coverage",
    "porosity",
    "correction",
    "developer",
    "processing",
    name="formulation_rule_category",
)
CONSULTATION_STATUS = postgresql.ENUM(
    "draft", "in_progress", "completed", "cancelled", name="consultation_status"
)
HAIR_TEXTURE = postgresql.ENUM("fine", "medium", "coarse", name="hair_texture")
SCALP_CONDITION = postgresql.ENUM(
    "normal", "sensitive", "irritated", "compromised", name="scalp_condition"
)
INTAKE_SOURCE = postgresql.ENUM(
    "ai_parsed", "manual_entry", "hybrid", name="intake_source"
)
RECOMMENDATION_TYPE = postgresql.ENUM(
    "safest", "fastest", "highest_fidelity", name="recommendation_type"
)
FORMULA_STATUS = postgresql.ENUM(
    "draft", "approved", "used", "discarded", "expired", name="formula_status"
)
FORMULA_ZONE = postgresql.ENUM(
    "root", "mid", "end", "all", "face_frame", "crown", name="formula_zone"
)
RISK_TYPE = postgresql.ENUM(
    "breakage",
    "banding",
    "overlap",
    "gray_coverage",
    "porosity_mismatch",
    "unrealistic_expectation",
    "allergic_reaction",
    "scalp_irritation",
    name="risk_type",
)
RISK_SEVERITY = postgresql.ENUM(
    "low", "medium", "high", "critical", name="risk_severity"
)

_VOLUME_RE = re.compile(r"\b(10|20|30|40)\b")
_RATIO_RE = re.compile(r"(\d+)\s*:\s*(\d+)")
_PCT_RE = re.compile(r"(\d{1,3})\s*%")


def _parse_volume(text: str) -> int | None:
    match = _VOLUME_RE.search(text)
    return int(match.group(1)) if match else None


def _parse_ratio(text: str) -> tuple[int, int] | None:
    match = _RATIO_RE.search(text)
    if not match:
        return None
    num, den = int(match.group(1)), int(match.group(2))
    if num > 0 and den > 0:
        return num, den
    return None


def _backfill_from_rule_value(rule_type: str, rule_value: dict) -> dict:
    """Return typed column updates parsed deterministically from rule_value JSON."""
    updates: dict = {}

    if rule_type == "developer":
        strengths = rule_value.get("strengths") or []
        for item in strengths:
            if not isinstance(item, dict):
                continue
            volume = item.get("volume")
            if volume and updates.get("developer_volume") is None:
                vol = _parse_volume(str(volume))
                if vol:
                    updates["developer_volume"] = vol
            lift = item.get("lift_levels")
            if isinstance(lift, (int, float)) and updates.get("max_lift_levels") is None:
                updates["max_lift_levels"] = float(lift)
        for override in rule_value.get("collection_overrides") or []:
            if not isinstance(override, dict):
                continue
            volume = override.get("volume") or override.get("required_volume")
            if volume and updates.get("developer_volume") is None:
                vol = _parse_volume(str(volume))
                if vol:
                    updates["developer_volume"] = vol

    elif rule_type == "mixing_ratio":
        default = rule_value.get("default")
        if isinstance(default, str):
            ratio = _parse_ratio(default)
            if ratio:
                updates["mixing_ratio_num"], updates["mixing_ratio_den"] = ratio
        if "mixing_ratio_num" not in updates:
            variants = rule_value.get("variants") or []
            for variant in variants:
                if isinstance(variant, dict) and variant.get("ratio"):
                    ratio = _parse_ratio(str(variant["ratio"]))
                    if ratio:
                        updates["mixing_ratio_num"], updates["mixing_ratio_den"] = ratio
                        break

    elif rule_type == "processing_time":
        ranges = rule_value.get("ranges") or []
        for item in ranges:
            if isinstance(item, dict) and isinstance(item.get("min_minutes"), int):
                updates["processing_time_min"] = item["min_minutes"]
                break

    elif rule_type == "gray_coverage":
        rules = rule_value.get("rules") or []
        for rule in rules:
            text = rule if isinstance(rule, str) else str(rule)
            match = _PCT_RE.search(text)
            if match:
                pct = int(match.group(1))
                if 0 <= pct <= 100:
                    updates["gray_coverage_pct"] = pct
                    break

    elif rule_type == "lift":
        rules = rule_value.get("rules") or []
        for item in rules:
            if isinstance(item, dict) and isinstance(item.get("lift_levels"), (int, float)):
                updates["max_lift_levels"] = float(item["lift_levels"])
                break

    return updates


def upgrade() -> None:
    # gen_random_uuid() requires pgcrypto on fresh PostgreSQL installs.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # updated_at trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create enums
    for enum_type in (
        COLOR_SCIENCE_CONFIDENCE,
        INTERMIX_RESTRICTION_TYPE,
        INTERMIX_EVIDENCE_STATUS,
        INTERMIX_RULE_SCOPE,
        FORMULATION_RULE_CATEGORY,
        CONSULTATION_STATUS,
        HAIR_TEXTURE,
        SCALP_CONDITION,
        INTAKE_SOURCE,
        RECOMMENDATION_TYPE,
        FORMULA_STATUS,
        FORMULA_ZONE,
        RISK_TYPE,
        RISK_SEVERITY,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    # A. universal_color_science
    op.create_table(
        "universal_color_science",
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("underlying_pigment", sa.String(), nullable=True),
        sa.Column("neutralizing_tone", sa.String(), nullable=True),
        sa.Column(
            "neutralizing_tone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("normalized_tone.normalized_tone_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exposure_stage", sa.String(), nullable=True),
        sa.Column("source_label", sa.String(), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_document.source_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "confidence",
            COLOR_SCIENCE_CONFIDENCE,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("level BETWEEN 1 AND 12", name="chk_ucs_level"),
        sa.PrimaryKeyConstraint("level"),
    )
    op.execute(
        """
        CREATE TRIGGER trg_universal_color_science_updated_at
            BEFORE UPDATE ON universal_color_science
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    op.execute(
        """
        INSERT INTO universal_color_science (
            level, underlying_pigment, neutralizing_tone, exposure_stage,
            source_label, confidence
        ) VALUES
            (1,  'Blue-black',     'Blue/Violet',  'Regrowth / darkest natural',  'Standard color theory curriculum', 'established'),
            (2,  'Blue-violet',    'Blue/Violet',  'Early lift',                  'Standard color theory curriculum', 'established'),
            (3,  'Blue-violet',    'Blue/Violet',  'Early lift',                  'Standard color theory curriculum', 'established'),
            (4,  'Red-brown',      'Green/Blue',   'Mid lift',                    'Standard color theory curriculum', 'established'),
            (5,  'Red-orange',     'Green',        'Mid lift',                    'Standard color theory curriculum', 'established'),
            (6,  'Orange',         'Blue',         'Mid lift',                    'Standard color theory curriculum', 'established'),
            (7,  'Orange-yellow',  'Blue/Violet',  'High lift',                   'Standard color theory curriculum', 'established'),
            (8,  'Yellow-orange',  'Violet/Ash',   'High lift',                   'Standard color theory curriculum', 'established'),
            (9,  'Yellow',         'Violet',       'High lift',                   'Standard color theory curriculum', 'established'),
            (10, 'Pale yellow',    'Violet/Ash',   'Pale stage / lightest natural','Standard color theory curriculum', 'established'),
            (11, NULL,             NULL,           'High-lift artificial',        'High-lift color theory (inferred)', 'inferred'),
            (12, NULL,             NULL,           'High-lift artificial / pre-lightened','High-lift color theory (inferred)', 'inferred')
        ON CONFLICT (level) DO NOTHING;
        """
    )
    op.execute(
        """
        UPDATE universal_color_science ucs
        SET neutralizing_tone_id = nt.normalized_tone_id
        FROM normalized_tone nt
        WHERE ucs.neutralizing_tone = nt.tone_name
          AND ucs.neutralizing_tone_id IS NULL;
        """
    )

    # B. line_technical_rule additive columns
    op.add_column("line_technical_rule", sa.Column("developer_volume", sa.Integer(), nullable=True))
    op.add_column(
        "line_technical_rule",
        sa.Column("max_lift_levels", sa.Numeric(2, 1), nullable=True),
    )
    op.add_column(
        "line_technical_rule", sa.Column("gray_coverage_pct", sa.Integer(), nullable=True)
    )
    op.add_column(
        "line_technical_rule", sa.Column("mixing_ratio_num", sa.Integer(), nullable=True)
    )
    op.add_column(
        "line_technical_rule", sa.Column("mixing_ratio_den", sa.Integer(), nullable=True)
    )
    op.add_column(
        "line_technical_rule", sa.Column("processing_time_min", sa.Integer(), nullable=True)
    )
    op.add_column(
        "line_technical_rule",
        sa.Column("applicable_hair_type", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "line_technical_rule",
        sa.Column("porosity_adjustment", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_check_constraint(
        "chk_ltr_has_payload",
        "line_technical_rule",
        "rule_value IS NOT NULL OR developer_volume IS NOT NULL "
        "OR max_lift_levels IS NOT NULL OR gray_coverage_pct IS NOT NULL "
        "OR mixing_ratio_num IS NOT NULL OR mixing_ratio_den IS NOT NULL "
        "OR processing_time_min IS NOT NULL OR applicable_hair_type IS NOT NULL "
        "OR porosity_adjustment IS NOT NULL",
    )
    op.create_check_constraint(
        "chk_ltr_gray_coverage_pct",
        "line_technical_rule",
        "gray_coverage_pct IS NULL OR gray_coverage_pct BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        "chk_ltr_developer_volume",
        "line_technical_rule",
        "developer_volume IS NULL OR (developer_volume > 0 AND developer_volume <= 100)",
    )
    op.create_check_constraint(
        "chk_ltr_processing_time_min",
        "line_technical_rule",
        "processing_time_min IS NULL OR processing_time_min > 0",
    )
    op.create_check_constraint(
        "chk_ltr_max_lift_levels",
        "line_technical_rule",
        "max_lift_levels IS NULL OR max_lift_levels >= 0",
    )
    op.create_check_constraint(
        "chk_ltr_mixing_ratio_pair",
        "line_technical_rule",
        "(mixing_ratio_num IS NULL AND mixing_ratio_den IS NULL) OR "
        "(mixing_ratio_num IS NOT NULL AND mixing_ratio_den IS NOT NULL "
        "AND mixing_ratio_num > 0 AND mixing_ratio_den > 0)",
    )

    # Backfill typed columns from existing JSON (safe skip on failure)
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT rule_id, rule_type, rule_value FROM line_technical_rule "
            "WHERE rule_value IS NOT NULL"
        )
    ).fetchall()

    for rule_id, rule_type, rule_value in rows:
        if not isinstance(rule_value, dict):
            continue
        try:
            updates = _backfill_from_rule_value(rule_type, rule_value)
        except Exception:
            continue
        if not updates:
            continue
        set_clause = ", ".join(f"{col} = :{col}" for col in updates)
        params = {"rule_id": rule_id, **updates}
        conn.execute(
            sa.text(
                f"UPDATE line_technical_rule SET {set_clause} WHERE rule_id = :rule_id"
            ),
            params,
        )

    # C. shade_intermixing_rule
    op.create_table(
        "shade_intermixing_rule",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "line_region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_line_region.line_region_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "applies_to_sub_range_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sub_range.sub_range_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "compatible_sub_range_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sub_range.sub_range_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "shade_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shade.shade_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "compatible_shade_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shade.shade_id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("rule_scope", INTERMIX_RULE_SCOPE, nullable=False),
        sa.Column("restriction_type", INTERMIX_RESTRICTION_TYPE, nullable=False),
        sa.Column("restriction_note", sa.Text(), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_document.source_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("evidence_status", INTERMIX_EVIDENCE_STATUS, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(rule_scope = 'shade_pair' AND shade_id IS NOT NULL) OR "
            "(rule_scope IN ('sub_range_internal_only', 'sub_range_isolated_from_line', "
            "'cross_sub_range') AND applies_to_sub_range_id IS NOT NULL)",
            name="chk_sir_scope_targets",
        ),
        sa.CheckConstraint(
            "rule_scope <> 'cross_sub_range' OR compatible_sub_range_id IS NOT NULL "
            "OR restriction_type = 'caution'",
            name="chk_sir_cross_sub_range_target",
        ),
    )
    op.create_index(
        "idx_shade_intermixing_applies",
        "shade_intermixing_rule",
        ["line_region_id", "applies_to_sub_range_id"],
    )
    op.execute(
        """
        CREATE TRIGGER trg_shade_intermixing_rule_updated_at
            BEFORE UPDATE ON shade_intermixing_rule
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # Seed Matrix SoColor intermixing rules (skipped when research data not loaded)
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_apply.sub_range_id,
            NULL,
            'sub_range_isolated_from_line'::intermix_rule_scope,
            'not_mixable'::intermix_restriction_type,
            'HD Series not mixable with any other SoColor shade (turns purple with naturals).',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_apply ON sr_apply.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_apply.sub_range_name ILIKE '%HD%'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_apply.sub_range_id,
            NULL,
            'sub_range_isolated_from_line'::intermix_rule_scope,
            'not_mixable'::intermix_restriction_type,
            'Ultra Blonde shades not intermixable with other SoColor shades.',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_apply ON sr_apply.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_apply.sub_range_name ILIKE '%Ultra Blonde%'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_ec.sub_range_id,
            sr_compat.sub_range_id,
            'cross_sub_range'::intermix_rule_scope,
            'caution'::intermix_restriction_type,
            'Extra Coverage intermixable with Blended & Reflect but may reduce gray coverage.',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_ec ON sr_ec.line_region_id = plr.line_region_id
        JOIN sub_range sr_compat ON sr_compat.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_ec.sub_range_name ILIKE '%Extra Coverage%'
          AND sr_compat.sub_range_name ILIKE '%Blended%'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_ec.sub_range_id,
            sr_compat.sub_range_id,
            'cross_sub_range'::intermix_rule_scope,
            'caution'::intermix_restriction_type,
            'Extra Coverage intermixable with Blended & Reflect but may reduce gray coverage.',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_ec ON sr_ec.line_region_id = plr.line_region_id
        JOIN sub_range sr_compat ON sr_compat.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_ec.sub_range_name ILIKE '%Extra Coverage%'
          AND sr_compat.sub_range_name ILIKE '%Reflect%'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_da.sub_range_id,
            NULL,
            'cross_sub_range'::intermix_rule_scope,
            'caution'::intermix_restriction_type,
            'DreamAge mixing with non-DreamAge shades is not recommended.',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_da ON sr_da.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_da.sub_range_name ILIKE '%DreamAge%'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO shade_intermixing_rule (
            rule_id, line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
            rule_scope, restriction_type, restriction_note, source_id, evidence_status
        )
        SELECT
            gen_random_uuid(),
            plr.line_region_id,
            sr_10.sub_range_id,
            NULL,
            'sub_range_internal_only'::intermix_rule_scope,
            'not_mixable'::intermix_restriction_type,
            'SoColor 10 min only mixable with other 10 min shades.',
            sd.source_id,
            'manufacturer_stated'::intermix_evidence_status
        FROM product_line_region plr
        JOIN product_line pl ON pl.line_id = plr.line_id
        JOIN brand b ON b.brand_id = pl.brand_id
        JOIN sub_range sr_10 ON sr_10.line_region_id = plr.line_region_id
        CROSS JOIN LATERAL (
            SELECT source_id FROM source_document
            WHERE source_title ILIKE '%2023 Matrix Manual%'
            LIMIT 1
        ) sd
        WHERE b.brand_name = 'Matrix'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
          AND plr.region_or_market = 'US'
          AND sr_10.sub_range_name ILIKE '%10 min%'
        ON CONFLICT DO NOTHING;
        """
    )

    # D. formulation_rule tables
    op.create_table(
        "formulation_rule",
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_name", sa.String(), nullable=False, unique=True),
        sa.Column("rule_priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rule_condition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_category", FORMULATION_RULE_CATEGORY, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_document.source_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("evidence_status", INTERMIX_EVIDENCE_STATUS, nullable=False),
        sa.Column("test_coverage", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "formulation_rule_brand",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand.brand_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "formulation_rule_line",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formulation_rule.rule_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "line_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_line.line_id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "idx_formulation_rule_active",
        "formulation_rule",
        ["is_active", "rule_category", "rule_priority"],
    )
    op.create_index(
        "idx_formulation_rule_condition_gin",
        "formulation_rule",
        ["rule_condition"],
        postgresql_using="gin",
    )
    op.execute(
        """
        CREATE TRIGGER trg_formulation_rule_updated_at
            BEFORE UPDATE ON formulation_rule
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    # Seed formulation rules
    op.execute(
        """
        INSERT INTO formulation_rule (
            rule_id, rule_name, rule_priority, rule_condition, rule_action,
            rule_category, evidence_status, test_coverage
        ) VALUES
        (
            gen_random_uuid(),
            'gray_coverage_high_natural_mix',
            50,
            '{"all_of": [{"field": "gray_percentage", "op": ">", "value": 50}, {"field": "natural_level", "op": "<=", "value": 6}]}'::jsonb,
            '{"set_developer_volume": 20, "require_natural_shade_mix": true, "natural_shade_ratio": 0.5}'::jsonb,
            'gray_coverage',
            'educator_reported',
            true
        ),
        (
            gen_random_uuid(),
            'high_porosity_reduce_developer_time',
            60,
            '{"any_of": [{"field": "porosity", "op": ">", "value": 7}]}'::jsonb,
            '{"adjust_developer_volume_delta": -10, "adjust_processing_time_minutes": -5}'::jsonb,
            'porosity',
            'educator_reported',
            false
        ),
        (
            gen_random_uuid(),
            'lift_over_four_prelighten_consult',
            40,
            '{"all_of": [{"field": "lift_levels", "op": ">", "value": 4}]}'::jsonb,
            '{"trigger_workflow": "pre_lightening_consultation", "risk_modifier": {"unrealistic_expectation": 0.3}}'::jsonb,
            'lift',
            'educator_reported',
            false
        ),
        (
            gen_random_uuid(),
            'artificial_color_lighter_correction',
            45,
            '{"all_of": [{"field": "existing_artificial_color", "op": "is_not_null", "value": true}, {"field": "desired_level", "op": ">", "value": "existing_level"}]}'::jsonb,
            '{"trigger_workflow": "color_correction", "risk_modifier": {"overlap": 0.25}}'::jsonb,
            'correction',
            'inferred',
            false
        ),
        (
            gen_random_uuid(),
            'fine_texture_high_lift_breakage_risk',
            70,
            '{"all_of": [{"field": "texture", "op": "=", "value": "fine"}, {"field": "lift_levels", "op": ">=", "value": 3}]}'::jsonb,
            '{"increase_risk_score": {"breakage": 0.35}}'::jsonb,
            'lift',
            'educator_reported',
            false
        ),
        (
            gen_random_uuid(),
            'matrix_socolor_resistant_gray_20vol',
            55,
            '{"all_of": [{"field": "gray_percentage", "op": ">=", "value": 50}]}'::jsonb,
            '{"set_developer_volume": 30, "add_step": {"zone": "root", "processing_time_adjustment": "+10min"}}'::jsonb,
            'gray_coverage',
            'manufacturer_stated',
            false
        )
        ON CONFLICT (rule_name) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO formulation_rule_brand (rule_id, brand_id)
        SELECT fr.rule_id, b.brand_id
        FROM formulation_rule fr
        CROSS JOIN brand b
        WHERE fr.rule_name = 'matrix_socolor_resistant_gray_20vol'
          AND b.brand_name = 'Matrix'
        ON CONFLICT DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO formulation_rule_line (rule_id, line_id)
        SELECT fr.rule_id, pl.line_id
        FROM formulation_rule fr
        JOIN brand b ON b.brand_name = 'Matrix'
        JOIN product_line pl ON pl.brand_id = b.brand_id
        WHERE fr.rule_name = 'matrix_socolor_resistant_gray_20vol'
          AND pl.product_line_name ILIKE '%SoColor%'
          AND pl.product_line_name NOT ILIKE '%Sync%'
        ON CONFLICT DO NOTHING;
        """
    )

    # E. Operational PRD tables
    op.create_table(
        "consultation",
        sa.Column("consultation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stylist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("salon_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            CONSULTATION_STATUS,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("ai_parsed_raw", sa.Text(), nullable=True),
        sa.Column("parser_confidence", sa.Numeric(3, 2), nullable=True),
        sa.CheckConstraint(
            "parser_confidence IS NULL OR parser_confidence BETWEEN 0 AND 1",
            name="chk_consultation_parser_confidence",
        ),
    )
    op.create_table(
        "hair_profile",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation.consultation_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("natural_level", sa.Integer(), nullable=False),
        sa.Column("existing_level", sa.Integer(), nullable=True),
        sa.Column("existing_artificial_color", sa.Text(), nullable=True),
        sa.Column("porosity", sa.Integer(), nullable=False),
        sa.Column("elasticity", sa.Integer(), nullable=False),
        sa.Column("gray_percentage", sa.Integer(), nullable=False),
        sa.Column("texture", HAIR_TEXTURE, nullable=False),
        sa.Column("scalp_condition", SCALP_CONDITION, nullable=False),
        sa.Column(
            "chemical_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("desired_result", sa.Text(), nullable=False),
        sa.Column("desired_tone", sa.Text(), nullable=True),
        sa.Column("desired_level", sa.Integer(), nullable=True),
        sa.Column("photo_urls", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("intake_source", INTAKE_SOURCE, nullable=False),
        sa.Column("data_confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("natural_level BETWEEN 1 AND 12", name="chk_hp_natural_level"),
        sa.CheckConstraint(
            "existing_level IS NULL OR existing_level BETWEEN 1 AND 12",
            name="chk_hp_existing_level",
        ),
        sa.CheckConstraint(
            "desired_level IS NULL OR desired_level BETWEEN 1 AND 12",
            name="chk_hp_desired_level",
        ),
        sa.CheckConstraint("porosity BETWEEN 1 AND 10", name="chk_hp_porosity"),
        sa.CheckConstraint("elasticity BETWEEN 1 AND 10", name="chk_hp_elasticity"),
        sa.CheckConstraint(
            "gray_percentage BETWEEN 0 AND 100", name="chk_hp_gray_percentage"
        ),
        sa.CheckConstraint(
            "data_confidence BETWEEN 0 AND 1", name="chk_hp_data_confidence"
        ),
    )
    op.create_index(
        "idx_hair_profile_chemical_history_gin",
        "hair_profile",
        ["chemical_history"],
        postgresql_using="gin",
    )
    op.execute(
        """
        CREATE TRIGGER trg_hair_profile_updated_at
            BEFORE UPDATE ON hair_profile
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    op.create_table(
        "formula",
        sa.Column("formula_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "consultation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation.consultation_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "line_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_line.line_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recommendation_type", RECOMMENDATION_TYPE, nullable=False),
        sa.Column(
            "status",
            FORMULA_STATUS,
            nullable=False,
            server_default="draft",
        ),
        sa.Column("risk_score", sa.Numeric(3, 2), nullable=False),
        sa.Column("total_processing_time", sa.Integer(), nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("stylist_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 1", name="chk_formula_risk_score"),
    )
    op.create_index("idx_formula_consultation", "formula", ["consultation_id", "status"])

    op.create_table(
        "formula_step",
        sa.Column("step_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "formula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formula.formula_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("zone", FORMULA_ZONE, nullable=False),
        sa.Column(
            "shade_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shade.shade_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "developer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("developer.developer_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mixing_ratio", sa.String(), nullable=True),
        sa.Column("quantity_grams", sa.Integer(), nullable=True),
        sa.Column("processing_time_minutes", sa.Integer(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("formula_id", "step_order", name="uq_formula_step_order"),
    )

    op.create_table(
        "risk_assessment",
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "formula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formula.formula_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("risk_type", RISK_TYPE, nullable=False),
        sa.Column("probability", sa.Numeric(3, 2), nullable=False),
        sa.Column("severity", RISK_SEVERITY, nullable=False),
        sa.Column(
            "contributing_factors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("requires_waiver", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("waiver_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("probability BETWEEN 0 AND 1", name="chk_risk_probability"),
    )
    op.create_index(
        "idx_risk_assessment_formula", "risk_assessment", ["formula_id", "risk_type"]
    )

    op.create_table(
        "formula_outcome",
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "formula_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("formula.formula_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("actual_result", sa.Text(), nullable=False),
        sa.Column("client_satisfaction", sa.Integer(), nullable=False),
        sa.Column("color_accuracy", sa.Integer(), nullable=True),
        sa.Column("condition_after", sa.Integer(), nullable=True),
        sa.Column("photos", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column(
            "corrective_service_needed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("corrective_service_description", sa.Text(), nullable=True),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "reported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "client_satisfaction BETWEEN 1 AND 10", name="chk_outcome_satisfaction"
        ),
        sa.CheckConstraint(
            "color_accuracy IS NULL OR color_accuracy BETWEEN 1 AND 10",
            name="chk_outcome_color_accuracy",
        ),
        sa.CheckConstraint(
            "condition_after IS NULL OR condition_after BETWEEN 1 AND 10",
            name="chk_outcome_condition_after",
        ),
    )

    op.create_index(
        "idx_shade_lookup",
        "shade",
        ["line_region_id", "sub_range_id", "shade_code"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_shade_lookup", table_name="shade")
    op.drop_table("formula_outcome")
    op.drop_index("idx_risk_assessment_formula", table_name="risk_assessment")
    op.drop_table("risk_assessment")
    op.drop_table("formula_step")
    op.drop_index("idx_formula_consultation", table_name="formula")
    op.drop_table("formula")
    op.execute("DROP TRIGGER IF EXISTS trg_hair_profile_updated_at ON hair_profile")
    op.drop_index("idx_hair_profile_chemical_history_gin", table_name="hair_profile")
    op.drop_table("hair_profile")
    op.drop_table("consultation")

    op.execute("DROP TRIGGER IF EXISTS trg_formulation_rule_updated_at ON formulation_rule")
    op.drop_index("idx_formulation_rule_condition_gin", table_name="formulation_rule")
    op.drop_index("idx_formulation_rule_active", table_name="formulation_rule")
    op.drop_table("formulation_rule_line")
    op.drop_table("formulation_rule_brand")
    op.drop_table("formulation_rule")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_shade_intermixing_rule_updated_at ON shade_intermixing_rule"
    )
    op.drop_index("idx_shade_intermixing_applies", table_name="shade_intermixing_rule")
    op.drop_table("shade_intermixing_rule")

    op.drop_constraint("chk_ltr_mixing_ratio_pair", "line_technical_rule", type_="check")
    op.drop_constraint("chk_ltr_max_lift_levels", "line_technical_rule", type_="check")
    op.drop_constraint("chk_ltr_processing_time_min", "line_technical_rule", type_="check")
    op.drop_constraint("chk_ltr_developer_volume", "line_technical_rule", type_="check")
    op.drop_constraint("chk_ltr_gray_coverage_pct", "line_technical_rule", type_="check")
    op.drop_constraint("chk_ltr_has_payload", "line_technical_rule", type_="check")
    op.drop_column("line_technical_rule", "porosity_adjustment")
    op.drop_column("line_technical_rule", "applicable_hair_type")
    op.drop_column("line_technical_rule", "processing_time_min")
    op.drop_column("line_technical_rule", "mixing_ratio_den")
    op.drop_column("line_technical_rule", "mixing_ratio_num")
    op.drop_column("line_technical_rule", "gray_coverage_pct")
    op.drop_column("line_technical_rule", "max_lift_levels")
    op.drop_column("line_technical_rule", "developer_volume")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_universal_color_science_updated_at ON universal_color_science"
    )
    op.drop_table("universal_color_science")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    for enum_type in (
        RISK_SEVERITY,
        RISK_TYPE,
        FORMULA_ZONE,
        FORMULA_STATUS,
        RECOMMENDATION_TYPE,
        INTAKE_SOURCE,
        SCALP_CONDITION,
        HAIR_TEXTURE,
        CONSULTATION_STATUS,
        FORMULATION_RULE_CATEGORY,
        INTERMIX_RULE_SCOPE,
        INTERMIX_EVIDENCE_STATUS,
        INTERMIX_RESTRICTION_TYPE,
        COLOR_SCIENCE_CONFIDENCE,
    ):
        enum_type.drop(op.get_bind(), checkfirst=True)
