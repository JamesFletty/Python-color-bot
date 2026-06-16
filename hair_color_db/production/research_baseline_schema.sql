-- =============================================================================
-- Research-layer baseline schema (Stage 12 package → PostgreSQL)
-- Derived from hair_color_db/stage12_package/H_schema_proposal.json
-- PostgreSQL 15+
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- ingestion_run
-- ---------------------------------------------------------------------------
CREATE TABLE ingestion_run (
    ingestion_run_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_label         VARCHAR NOT NULL UNIQUE,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ NULL,
    tooling_version     VARCHAR NULL,
    notes               TEXT NULL
);

-- ---------------------------------------------------------------------------
-- brand / product_line / product_line_region / sub_range
-- ---------------------------------------------------------------------------
CREATE TABLE brand (
    brand_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_name          VARCHAR NOT NULL UNIQUE,
    parent_company      VARCHAR NULL,
    official_brand_url  VARCHAR NULL
);

CREATE TABLE product_line (
    line_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            UUID NOT NULL REFERENCES brand(brand_id) ON DELETE RESTRICT,
    product_line_name   VARCHAR NOT NULL,
    line_category       VARCHAR NULL,
    code_grammar        VARCHAR NULL,
    apparent_status     VARCHAR NULL,
    official_line_url   VARCHAR NULL,
    UNIQUE (brand_id, product_line_name)
);

CREATE TABLE product_line_region (
    line_region_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id             UUID NOT NULL REFERENCES product_line(line_id) ON DELETE RESTRICT,
    region_or_market    VARCHAR NOT NULL,
    canonical_key       VARCHAR NOT NULL UNIQUE,
    discontinued_status VARCHAR NULL,
    notes               JSONB NULL
);

CREATE TABLE sub_range (
    sub_range_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_region_id      UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    sub_range_name      VARCHAR NOT NULL,
    notes               JSONB NULL,
    UNIQUE (line_region_id, sub_range_name)
);

-- ---------------------------------------------------------------------------
-- source_document
-- ---------------------------------------------------------------------------
CREATE TABLE source_document (
    source_id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_title                VARCHAR NOT NULL,
    source_type                 VARCHAR NULL,
    source_url                  VARCHAR NULL,
    publisher_domain            VARCHAR NULL,
    publication_or_revision_date VARCHAR NULL,
    file_type                   VARCHAR NULL,
    access_status               VARCHAR NULL,
    source_priority_tier        INT NULL,
    region_or_market            VARCHAR NULL,
    retrieved_at                TIMESTAMPTZ NULL,
    content_hash                VARCHAR NULL
);

-- ---------------------------------------------------------------------------
-- shade_raw (append-only) + shade (normalized)
-- ---------------------------------------------------------------------------
CREATE TABLE shade_raw (
    shade_raw_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_region_id              UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    sub_range_id                UUID NULL REFERENCES sub_range(sub_range_id) ON DELETE RESTRICT,
    shade_code_raw              VARCHAR NOT NULL,
    shade_name_raw              VARCHAR NULL,
    level_raw                   NUMERIC NULL,
    tone_codes_raw              JSONB NULL,
    tone_descriptions_raw       JSONB NULL,
    gray_coverage_claim_raw     TEXT NULL,
    lift_capability_raw         TEXT NULL,
    mixing_ratio_raw            TEXT NULL,
    developer_recommendations_raw JSONB NULL,
    processing_time_raw         TEXT NULL,
    special_usage_notes_raw     TEXT NULL,
    official_swatch_image_exists BOOLEAN NULL,
    source_id                   UUID NOT NULL REFERENCES source_document(source_id) ON DELETE RESTRICT,
    source_confidence           VARCHAR NULL,
    evidence_status             VARCHAR NULL,
    assumptions                 JSONB NULL,
    data_gaps                   JSONB NULL,
    extracted_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    ingestion_run_id            UUID NOT NULL REFERENCES ingestion_run(ingestion_run_id) ON DELETE RESTRICT
);

CREATE TABLE shade (
    shade_id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shade_raw_id                UUID NOT NULL REFERENCES shade_raw(shade_raw_id) ON DELETE RESTRICT,
    line_region_id              UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    sub_range_id                UUID NULL REFERENCES sub_range(sub_range_id) ON DELETE RESTRICT,
    shade_code                  VARCHAR NOT NULL,
    shade_name                  VARCHAR NULL,
    level                       NUMERIC NULL,
    color_type                  VARCHAR NULL,
    gray_coverage_claim           TEXT NULL,
    lift_levels                 TEXT NULL,
    mixing_ratio                TEXT NULL,
    mixing_ratio_inherited      BOOLEAN NOT NULL DEFAULT FALSE,
    processing_time_minutes     INT NULL,
    processing_time_inherited   BOOLEAN NOT NULL DEFAULT FALSE,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (line_region_id, sub_range_id, shade_code)
);

CREATE INDEX idx_shade_lookup ON shade (line_region_id, sub_range_id, shade_code);

-- ---------------------------------------------------------------------------
-- tone normalization
-- ---------------------------------------------------------------------------
CREATE TABLE normalized_tone (
    normalized_tone_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tone_name           VARCHAR NOT NULL UNIQUE
);

CREATE TABLE tone_code_reference (
    tone_code_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_region_id          UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    manufacturer_tone_code  VARCHAR NOT NULL,
    manufacturer_term       VARCHAR NULL,
    manufacturer_definition TEXT NULL,
    confidence              VARCHAR NULL,
    notes_on_ambiguity      JSONB NULL,
    source_id               UUID NULL REFERENCES source_document(source_id) ON DELETE SET NULL,
    UNIQUE (line_region_id, manufacturer_tone_code)
);

CREATE TABLE tone_normalization (
    tone_code_id            UUID NOT NULL REFERENCES tone_code_reference(tone_code_id) ON DELETE CASCADE,
    normalized_tone_id      UUID NOT NULL REFERENCES normalized_tone(normalized_tone_id) ON DELETE CASCADE,
    mapping_rationale       TEXT NULL,
    mapping_confidence      VARCHAR NULL,
    ambiguity_flag          BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (tone_code_id, normalized_tone_id)
);

CREATE TABLE shade_tone_code (
    shade_id        UUID NOT NULL REFERENCES shade(shade_id) ON DELETE CASCADE,
    tone_code_id    UUID NOT NULL REFERENCES tone_code_reference(tone_code_id) ON DELETE CASCADE,
    position        INT NOT NULL,
    PRIMARY KEY (shade_id, tone_code_id)
);

-- ---------------------------------------------------------------------------
-- line_technical_rule (+ typed columns added by operational migration)
-- ---------------------------------------------------------------------------
CREATE TABLE line_technical_rule (
    rule_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_region_id          UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    rule_type               VARCHAR NOT NULL,
    rule_value              JSONB NOT NULL,
    applies_to_sub_range_id UUID NULL REFERENCES sub_range(sub_range_id) ON DELETE RESTRICT,
    source_id               UUID NOT NULL REFERENCES source_document(source_id) ON DELETE RESTRICT,
    source_confidence       VARCHAR NULL,
    evidence_status         VARCHAR NULL
);

-- ---------------------------------------------------------------------------
-- developer / line_developer (stubs for schema completeness)
-- ---------------------------------------------------------------------------
CREATE TABLE developer (
    developer_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            UUID NULL REFERENCES brand(brand_id) ON DELETE SET NULL,
    developer_name      VARCHAR NOT NULL,
    volume              INT NULL,
    percent_peroxide    NUMERIC NULL
);

CREATE TABLE line_developer (
    line_region_id      UUID NOT NULL REFERENCES product_line_region(line_region_id) ON DELETE CASCADE,
    developer_id        UUID NOT NULL REFERENCES developer(developer_id) ON DELETE CASCADE,
    usage_context       TEXT NULL,
    PRIMARY KEY (line_region_id, developer_id)
);

-- ---------------------------------------------------------------------------
-- provenance / versioning / issues (stubs)
-- ---------------------------------------------------------------------------
CREATE TABLE record_source (
    record_table    VARCHAR NOT NULL,
    record_id         UUID NOT NULL,
    source_id         UUID NOT NULL REFERENCES source_document(source_id) ON DELETE CASCADE,
    role              VARCHAR NOT NULL DEFAULT 'primary',
    PRIMARY KEY (record_table, record_id, source_id)
);

CREATE TABLE record_version (
    version_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_table        VARCHAR NOT NULL,
    record_id           UUID NOT NULL,
    superseded_by       UUID NULL,
    valid_from          TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to            TIMESTAMPTZ NULL,
    change_reason       TEXT NULL,
    ingestion_run_id    UUID NULL REFERENCES ingestion_run(ingestion_run_id) ON DELETE SET NULL
);

CREATE TABLE issue_log (
    issue_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_key   VARCHAR NULL,
    record_ref      VARCHAR NULL,
    issue_type      VARCHAR NOT NULL,
    severity        VARCHAR NULL,
    details         TEXT NULL,
    status          VARCHAR NOT NULL DEFAULT 'open',
    stage_raised    INT NULL
);
