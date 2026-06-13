"""SQLite DDL derived from hair_color_db/stage10_schema/schema_proposal.json."""

from __future__ import annotations

# Practical Phase 1 subset aligned with schema_proposal tables:
# brand, product_line, shade, shade_normalized_tone, tone_normalization,
# line_technical_rule, source_document (embedded on shade/rule rows).

DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS brand (
        brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_line (
        line_id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER NOT NULL REFERENCES brand(brand_id),
        product_line_name TEXT NOT NULL,
        canonical_key TEXT NOT NULL,
        color_type TEXT,
        region_or_market TEXT,
        discontinued_status TEXT,
        UNIQUE(brand_id, product_line_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shade (
        shade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER NOT NULL REFERENCES product_line(line_id),
        canonical_key TEXT NOT NULL,
        shade_code TEXT NOT NULL,
        shade_name TEXT,
        sub_range TEXT NOT NULL DEFAULT '',
        level REAL,
        color_type TEXT,
        gray_coverage_claim TEXT,
        lift_levels TEXT,
        mixing_ratio TEXT,
        developer_options TEXT,
        processing_time_minutes INTEGER,
        special_usage_notes TEXT,
        manufacturer_tone_codes TEXT,
        manufacturer_tone_descriptions TEXT,
        region_or_market TEXT,
        discontinued_status TEXT,
        source_url TEXT,
        source_document TEXT,
        source_type TEXT,
        source_publication_date TEXT,
        source_confidence TEXT,
        evidence_status TEXT,
        assumptions TEXT,
        data_gaps TEXT,
        UNIQUE(line_id, shade_code, sub_range)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shade_normalized_tone (
        shade_id INTEGER NOT NULL REFERENCES shade(shade_id) ON DELETE CASCADE,
        tone_name TEXT NOT NULL,
        position INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (shade_id, tone_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tone_normalization (
        mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER REFERENCES product_line(line_id),
        canonical_key TEXT NOT NULL,
        manufacturer_tone_code TEXT NOT NULL,
        manufacturer_term TEXT,
        normalized_tones TEXT NOT NULL,
        mapping_rationale TEXT,
        mapping_confidence TEXT,
        ambiguity_flag INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        UNIQUE(canonical_key, manufacturer_tone_code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS line_technical_rule (
        rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER NOT NULL REFERENCES product_line(line_id),
        canonical_key TEXT NOT NULL,
        rule_type TEXT NOT NULL CHECK (
            rule_type IN (
                'mixing_ratio',
                'developer',
                'processing_time',
                'gray_coverage',
                'lift',
                'tone_legend',
                'special_usage',
                'color_type'
            )
        ),
        rule_value TEXT NOT NULL,
        source_url TEXT,
        source_document TEXT,
        source_confidence TEXT,
        evidence_status TEXT,
        assumptions TEXT,
        data_gaps TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_shade_code ON shade(shade_code)",
    "CREATE INDEX IF NOT EXISTS idx_shade_canonical_key ON shade(canonical_key)",
    "CREATE INDEX IF NOT EXISTS idx_shade_level ON shade(level)",
    "CREATE INDEX IF NOT EXISTS idx_shade_line_id ON shade(line_id)",
    "CREATE INDEX IF NOT EXISTS idx_tone_norm_canonical ON tone_normalization(canonical_key)",
    "CREATE INDEX IF NOT EXISTS idx_ltr_line_type ON line_technical_rule(line_id, rule_type)",
)

RULE_TYPE_FIELD_MAP: dict[str, str] = {
    "default_mixing_ratio": "mixing_ratio",
    "developer_options": "developer",
    "developer_strengths_if_stated": "developer",
    "processing_time_ranges": "processing_time",
    "gray_coverage_rules": "gray_coverage",
    "lift_rules": "lift",
    "tone_family_legend": "tone_legend",
    "special_usage_notes": "special_usage",
    "color_type": "color_type",
}
