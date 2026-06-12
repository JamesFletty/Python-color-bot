-- =============================================================================
-- Operational / production schema extensions for the deterministic hair color
-- formula engine.  Assumes the research-layer tables from H_schema_proposal.json
-- already exist (brand, product_line, shade, line_technical_rule, etc.).
-- PostgreSQL 15+
-- =============================================================================

-- UUID generation: gen_random_uuid() requires pgcrypto on fresh PostgreSQL installs.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Shared trigger: maintain updated_at on row change
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- ENUM types (operational layer)
-- ---------------------------------------------------------------------------
CREATE TYPE color_science_confidence AS ENUM ('established', 'debated', 'inferred');

CREATE TYPE intermix_restriction_type AS ENUM (
    'not_mixable',
    'caution',
    'ratio_required',
    'developer_override'
);

CREATE TYPE intermix_evidence_status AS ENUM (
    'confirmed',
    'manufacturer_stated',
    'educator_reported',
    'inferred'
);

CREATE TYPE intermix_rule_scope AS ENUM (
    'shade_pair',
    'sub_range_internal_only',
    'sub_range_isolated_from_line',
    'cross_sub_range'
);

CREATE TYPE formulation_rule_category AS ENUM (
    'lift',
    'tone',
    'neutralization',
    'gray_coverage',
    'porosity',
    'correction',
    'developer',
    'processing'
);

CREATE TYPE consultation_status AS ENUM (
    'draft',
    'in_progress',
    'completed',
    'cancelled'
);

CREATE TYPE hair_texture AS ENUM ('fine', 'medium', 'coarse');

CREATE TYPE scalp_condition AS ENUM ('normal', 'sensitive', 'irritated', 'compromised');

CREATE TYPE intake_source AS ENUM ('ai_parsed', 'manual_entry', 'hybrid');

CREATE TYPE recommendation_type AS ENUM ('safest', 'fastest', 'highest_fidelity');

CREATE TYPE formula_status AS ENUM ('draft', 'approved', 'used', 'discarded', 'expired');

CREATE TYPE formula_zone AS ENUM ('root', 'mid', 'end', 'all', 'face_frame', 'crown');

CREATE TYPE risk_type AS ENUM (
    'breakage',
    'banding',
    'overlap',
    'gray_coverage',
    'porosity_mismatch',
    'unrealistic_expectation',
    'allergic_reaction',
    'scalp_irritation'
);

CREATE TYPE risk_severity AS ENUM ('low', 'medium', 'high', 'critical');

-- ---------------------------------------------------------------------------
-- A. universal_color_science
-- ---------------------------------------------------------------------------
CREATE TABLE universal_color_science (
    level                   INT PRIMARY KEY,
    underlying_pigment      VARCHAR NULL,
    neutralizing_tone       VARCHAR NULL,
    neutralizing_tone_id    UUID NULL REFERENCES normalized_tone(normalized_tone_id) ON DELETE SET NULL,
    exposure_stage          VARCHAR NULL,
    source_label            VARCHAR NOT NULL,
    source_id               UUID NULL REFERENCES source_document(source_id) ON DELETE SET NULL,
    confidence              color_science_confidence NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_ucs_level CHECK (level BETWEEN 1 AND 12)
);

CREATE TRIGGER trg_universal_color_science_updated_at
    BEFORE UPDATE ON universal_color_science
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE universal_color_science IS
    'Universal hair-color science facts (underlying pigment, neutralization) used by the deterministic engine across all brands.';

-- Seed levels 1-12 (levels 11-12 are high-lift / artificial categories)
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
    (12, NULL,             NULL,           'High-lift artificial / pre-lightened','High-lift color theory (inferred)', 'inferred');

-- Link neutralizing_tone_id only when seed text matches a single normalized_tone.tone_name
-- exactly (compound labels such as 'Blue/Violet' or 'Violet/Ash' are intentionally left NULL).
UPDATE universal_color_science ucs
SET neutralizing_tone_id = nt.normalized_tone_id
FROM normalized_tone nt
WHERE ucs.neutralizing_tone = nt.tone_name
  AND ucs.neutralizing_tone_id IS NULL;

-- ---------------------------------------------------------------------------
-- B. line_technical_rule — additive typed columns (rule_value preserved)
-- ---------------------------------------------------------------------------
ALTER TABLE line_technical_rule
    ADD COLUMN IF NOT EXISTS developer_volume      INT NULL,
    ADD COLUMN IF NOT EXISTS max_lift_levels       NUMERIC(2, 1) NULL,
    ADD COLUMN IF NOT EXISTS gray_coverage_pct     INT NULL,
    ADD COLUMN IF NOT EXISTS mixing_ratio_num      INT NULL,
    ADD COLUMN IF NOT EXISTS mixing_ratio_den      INT NULL,
    ADD COLUMN IF NOT EXISTS processing_time_min   INT NULL,
    ADD COLUMN IF NOT EXISTS applicable_hair_type  VARCHAR[] NULL,
    ADD COLUMN IF NOT EXISTS porosity_adjustment   JSONB NULL;

ALTER TABLE line_technical_rule
    ADD CONSTRAINT chk_ltr_has_payload CHECK (
        rule_value IS NOT NULL
        OR developer_volume IS NOT NULL
        OR max_lift_levels IS NOT NULL
        OR gray_coverage_pct IS NOT NULL
        OR mixing_ratio_num IS NOT NULL
        OR mixing_ratio_den IS NOT NULL
        OR processing_time_min IS NOT NULL
        OR applicable_hair_type IS NOT NULL
        OR porosity_adjustment IS NOT NULL
    ),
    ADD CONSTRAINT chk_ltr_gray_coverage_pct
        CHECK (gray_coverage_pct IS NULL OR gray_coverage_pct BETWEEN 0 AND 100),
    ADD CONSTRAINT chk_ltr_developer_volume
        CHECK (developer_volume IS NULL OR (developer_volume > 0 AND developer_volume <= 100)),
    ADD CONSTRAINT chk_ltr_processing_time_min
        CHECK (processing_time_min IS NULL OR processing_time_min > 0),
    ADD CONSTRAINT chk_ltr_max_lift_levels
        CHECK (max_lift_levels IS NULL OR max_lift_levels >= 0),
    ADD CONSTRAINT chk_ltr_mixing_ratio_pair CHECK (
        (mixing_ratio_num IS NULL AND mixing_ratio_den IS NULL)
        OR (
            mixing_ratio_num IS NOT NULL
            AND mixing_ratio_den IS NOT NULL
            AND mixing_ratio_num > 0
            AND mixing_ratio_den > 0
        )
    );

COMMENT ON COLUMN line_technical_rule.developer_volume IS
    'Additive typed column; salon volume convention (e.g. 10 = 10 vol). Original rule_value JSON is always preserved.';
COMMENT ON COLUMN line_technical_rule.porosity_adjustment IS
    'JSONB adjustments keyed by porosity band, e.g. {"high": {"developer_volume_delta": -10}}.';

-- ---------------------------------------------------------------------------
-- C. shade_intermixing_rule
-- ---------------------------------------------------------------------------
CREATE TABLE shade_intermixing_rule (
    rule_id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_region_id              UUID NULL REFERENCES product_line_region(line_region_id) ON DELETE RESTRICT,
    applies_to_sub_range_id     UUID NULL REFERENCES sub_range(sub_range_id) ON DELETE RESTRICT,
    compatible_sub_range_id     UUID NULL REFERENCES sub_range(sub_range_id) ON DELETE RESTRICT,
    shade_id                    UUID NULL REFERENCES shade(shade_id) ON DELETE RESTRICT,
    compatible_shade_id         UUID NULL REFERENCES shade(shade_id) ON DELETE RESTRICT,
    rule_scope                  intermix_rule_scope NOT NULL,
    restriction_type            intermix_restriction_type NOT NULL,
    restriction_note            TEXT NOT NULL,
    source_id                   UUID NOT NULL REFERENCES source_document(source_id) ON DELETE RESTRICT,
    evidence_status             intermix_evidence_status NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_sir_scope_targets CHECK (
        (rule_scope = 'shade_pair' AND shade_id IS NOT NULL)
        OR (rule_scope IN (
            'sub_range_internal_only',
            'sub_range_isolated_from_line',
            'cross_sub_range'
        ) AND applies_to_sub_range_id IS NOT NULL)
    ),
    CONSTRAINT chk_sir_cross_sub_range_target CHECK (
        rule_scope <> 'cross_sub_range'
        OR compatible_sub_range_id IS NOT NULL
        OR restriction_type = 'caution'
    )
);

CREATE INDEX idx_shade_intermixing_applies
    ON shade_intermixing_rule (line_region_id, applies_to_sub_range_id);

CREATE TRIGGER trg_shade_intermixing_rule_updated_at
    BEFORE UPDATE ON shade_intermixing_rule
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE shade_intermixing_rule IS
    'Compact intermixing safety rules. sub_range_isolated_from_line = cannot mix with any other sub-range in the line; '
    'sub_range_internal_only = only mix within the same sub-range; cross_sub_range with NULL compatible_sub_range_id '
    'and caution = discouraged mixing with all non-source sub-ranges (e.g. DreamAge).';

-- ---------------------------------------------------------------------------
-- D. formulation_rule + applicability join tables
-- ---------------------------------------------------------------------------
CREATE TABLE formulation_rule (
    rule_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name           VARCHAR NOT NULL UNIQUE,
    rule_priority       INT NOT NULL DEFAULT 100,
    rule_condition      JSONB NOT NULL,
    rule_action         JSONB NOT NULL,
    rule_category       formulation_rule_category NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_id           UUID NULL REFERENCES source_document(source_id) ON DELETE SET NULL,
    evidence_status     intermix_evidence_status NOT NULL,
    test_coverage       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE formulation_rule_brand (
    rule_id     UUID NOT NULL REFERENCES formulation_rule(rule_id) ON DELETE CASCADE,
    brand_id    UUID NOT NULL REFERENCES brand(brand_id) ON DELETE CASCADE,
    PRIMARY KEY (rule_id, brand_id)
);

CREATE TABLE formulation_rule_line (
    rule_id     UUID NOT NULL REFERENCES formulation_rule(rule_id) ON DELETE CASCADE,
    line_id     UUID NOT NULL REFERENCES product_line(line_id) ON DELETE CASCADE,
    PRIMARY KEY (rule_id, line_id)
);

CREATE INDEX idx_formulation_rule_active
    ON formulation_rule (is_active, rule_category, rule_priority);

CREATE INDEX idx_formulation_rule_condition_gin
    ON formulation_rule USING GIN (rule_condition);

CREATE TRIGGER trg_formulation_rule_updated_at
    BEFORE UPDATE ON formulation_rule
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE formulation_rule IS
    'Deterministic engine rules. No brand rows = universal; brand rows without line rows = all lines in those brands; '
    'line rows = listed lines only. Applicability via formulation_rule_brand / formulation_rule_line join tables.';

-- Seed formulation rules (universal + Matrix SoColor line-scoped example)
INSERT INTO formulation_rule (
    rule_name, rule_priority, rule_condition, rule_action,
    rule_category, evidence_status, test_coverage
) VALUES
(
    'gray_coverage_high_natural_mix', 50,
    '{"all_of": [{"field": "gray_percentage", "op": ">", "value": 50}, {"field": "natural_level", "op": "<=", "value": 6}]}'::jsonb,
    '{"set_developer_volume": 20, "require_natural_shade_mix": true, "natural_shade_ratio": 0.5}'::jsonb,
    'gray_coverage', 'educator_reported', TRUE
),
(
    'high_porosity_reduce_developer_time', 60,
    '{"any_of": [{"field": "porosity", "op": ">", "value": 7}]}'::jsonb,
    '{"adjust_developer_volume_delta": -10, "adjust_processing_time_minutes": -5}'::jsonb,
    'porosity', 'educator_reported', FALSE
),
(
    'lift_over_four_prelighten_consult', 40,
    '{"all_of": [{"field": "lift_levels", "op": ">", "value": 4}]}'::jsonb,
    '{"trigger_workflow": "pre_lightening_consultation", "risk_modifier": {"unrealistic_expectation": 0.3}}'::jsonb,
    'lift', 'educator_reported', FALSE
),
(
    'artificial_color_lighter_correction', 45,
    '{"all_of": [{"field": "existing_artificial_color", "op": "is_not_null", "value": true}, {"field": "desired_level", "op": ">", "value": "existing_level"}]}'::jsonb,
    '{"trigger_workflow": "color_correction", "risk_modifier": {"overlap": 0.25}}'::jsonb,
    'correction', 'inferred', FALSE
),
(
    'fine_texture_high_lift_breakage_risk', 70,
    '{"all_of": [{"field": "texture", "op": "=", "value": "fine"}, {"field": "lift_levels", "op": ">=", "value": 3}]}'::jsonb,
    '{"increase_risk_score": {"breakage": 0.35}}'::jsonb,
    'lift', 'educator_reported', FALSE
),
(
    'matrix_socolor_resistant_gray_20vol', 55,
    '{"all_of": [{"field": "gray_percentage", "op": ">=", "value": 50}]}'::jsonb,
    '{"set_developer_volume": 20, "add_step": {"zone": "root", "processing_time_adjustment": "+10min"}}'::jsonb,
    'gray_coverage', 'manufacturer_stated', FALSE
)
ON CONFLICT (rule_name) DO NOTHING;

INSERT INTO formulation_rule_brand (rule_id, brand_id)
SELECT fr.rule_id, b.brand_id
FROM formulation_rule fr
CROSS JOIN brand b
WHERE fr.rule_name = 'matrix_socolor_resistant_gray_20vol'
  AND b.brand_name = 'Matrix'
ON CONFLICT DO NOTHING;

INSERT INTO formulation_rule_line (rule_id, line_id)
SELECT fr.rule_id, pl.line_id
FROM formulation_rule fr
JOIN brand b ON b.brand_name = 'Matrix'
JOIN product_line pl ON pl.brand_id = b.brand_id
WHERE fr.rule_name = 'matrix_socolor_resistant_gray_20vol'
  AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%'
ON CONFLICT DO NOTHING;

-- Seed Matrix SoColor intermixing rules (requires research sub_range rows)
INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, rule_scope, restriction_type,
    restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_apply.sub_range_id,
    'sub_range_isolated_from_line', 'not_mixable',
    'HD Series not mixable with any other SoColor shade (turns purple with naturals).',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_apply ON sr_apply.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_apply.sub_range_name ILIKE '%HD%' AND sd.source_id IS NOT NULL;

INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, rule_scope, restriction_type,
    restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_apply.sub_range_id,
    'sub_range_isolated_from_line', 'not_mixable',
    'Ultra Blonde shades not intermixable with other SoColor shades.',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_apply ON sr_apply.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_apply.sub_range_name ILIKE '%Ultra Blonde%' AND sd.source_id IS NOT NULL;

INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
    rule_scope, restriction_type, restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_ec.sub_range_id, sr_compat.sub_range_id,
    'cross_sub_range', 'caution',
    'Extra Coverage intermixable with Blended & Reflect but may reduce gray coverage.',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_ec ON sr_ec.line_region_id = plr.line_region_id
JOIN sub_range sr_compat ON sr_compat.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_ec.sub_range_name ILIKE '%Extra Coverage%'
  AND sr_compat.sub_range_name ILIKE '%Blended%' AND sd.source_id IS NOT NULL;

INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, compatible_sub_range_id,
    rule_scope, restriction_type, restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_ec.sub_range_id, sr_compat.sub_range_id,
    'cross_sub_range', 'caution',
    'Extra Coverage intermixable with Blended & Reflect but may reduce gray coverage.',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_ec ON sr_ec.line_region_id = plr.line_region_id
JOIN sub_range sr_compat ON sr_compat.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_ec.sub_range_name ILIKE '%Extra Coverage%'
  AND sr_compat.sub_range_name ILIKE '%Reflect%' AND sd.source_id IS NOT NULL;

INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, rule_scope, restriction_type,
    restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_da.sub_range_id,
    'cross_sub_range', 'caution',
    'DreamAge mixing with non-DreamAge shades is not recommended.',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_da ON sr_da.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_da.sub_range_name ILIKE '%DreamAge%' AND sd.source_id IS NOT NULL;

INSERT INTO shade_intermixing_rule (
    line_region_id, applies_to_sub_range_id, rule_scope, restriction_type,
    restriction_note, source_id, evidence_status
)
SELECT plr.line_region_id, sr_10.sub_range_id,
    'sub_range_internal_only', 'not_mixable',
    'SoColor 10 min only mixable with other 10 min shades.',
    sd.source_id, 'manufacturer_stated'
FROM product_line_region plr
JOIN product_line pl ON pl.line_id = plr.line_id
JOIN brand b ON b.brand_id = pl.brand_id
JOIN sub_range sr_10 ON sr_10.line_region_id = plr.line_region_id
CROSS JOIN LATERAL (
    SELECT source_id FROM source_document WHERE source_title ILIKE '%2023 Matrix Manual%' LIMIT 1
) sd
WHERE b.brand_name = 'Matrix' AND pl.product_line_name ILIKE '%SoColor%'
  AND pl.product_line_name NOT ILIKE '%Sync%' AND plr.region_or_market = 'US'
  AND sr_10.sub_range_name ILIKE '%10 min%' AND sd.source_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- E. Operational PRD domain tables
-- ---------------------------------------------------------------------------
CREATE TABLE consultation (
    consultation_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           UUID NULL,
    stylist_id          UUID NOT NULL,
    salon_id            UUID NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ NULL,
    status              consultation_status NOT NULL DEFAULT 'draft',
    ai_parsed_raw       TEXT NULL,
    parser_confidence   NUMERIC(3, 2) NULL,
    CONSTRAINT chk_consultation_parser_confidence
        CHECK (parser_confidence IS NULL OR parser_confidence BETWEEN 0 AND 1)
);

COMMENT ON COLUMN consultation.client_id IS 'External identity reference; not FK-enforced.';
COMMENT ON COLUMN consultation.stylist_id IS 'External identity reference; not FK-enforced.';
COMMENT ON COLUMN consultation.salon_id IS 'External identity reference; not FK-enforced.';

CREATE TABLE hair_profile (
    profile_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id             UUID NOT NULL REFERENCES consultation(consultation_id) ON DELETE CASCADE,
    natural_level               INT NOT NULL,
    existing_level              INT NULL,
    existing_artificial_color   TEXT NULL,
    porosity                    INT NOT NULL,
    elasticity                  INT NOT NULL,
    gray_percentage             INT NOT NULL,
    texture                     hair_texture NOT NULL,
    scalp_condition             scalp_condition NOT NULL,
    chemical_history            JSONB NOT NULL DEFAULT '[]'::jsonb,
    desired_result              TEXT NOT NULL,
    desired_tone                TEXT NULL,
    desired_level               INT NULL,
    photo_urls                  TEXT[] NULL,
    intake_source               intake_source NOT NULL,
    data_confidence             NUMERIC(3, 2) NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_hp_natural_level CHECK (natural_level BETWEEN 1 AND 12),
    CONSTRAINT chk_hp_existing_level CHECK (existing_level IS NULL OR existing_level BETWEEN 1 AND 12),
    CONSTRAINT chk_hp_desired_level CHECK (desired_level IS NULL OR desired_level BETWEEN 1 AND 12),
    CONSTRAINT chk_hp_porosity CHECK (porosity BETWEEN 1 AND 10),
    CONSTRAINT chk_hp_elasticity CHECK (elasticity BETWEEN 1 AND 10),
    CONSTRAINT chk_hp_gray_percentage CHECK (gray_percentage BETWEEN 0 AND 100),
    CONSTRAINT chk_hp_data_confidence CHECK (data_confidence BETWEEN 0 AND 1)
);

COMMENT ON COLUMN hair_profile.desired_tone IS
    'Free-text desired tone; future mapping to trend lexicon / normalized tone taxonomy planned.';

CREATE INDEX idx_hair_profile_chemical_history_gin
    ON hair_profile USING GIN (chemical_history);

CREATE TRIGGER trg_hair_profile_updated_at
    BEFORE UPDATE ON hair_profile
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE formula (
    formula_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id         UUID NOT NULL REFERENCES consultation(consultation_id) ON DELETE RESTRICT,
    line_id                 UUID NOT NULL REFERENCES product_line(line_id) ON DELETE RESTRICT,
    recommendation_type     recommendation_type NOT NULL,
    status                  formula_status NOT NULL DEFAULT 'draft',
    risk_score              NUMERIC(3, 2) NOT NULL,
    total_processing_time   INT NOT NULL,
    ai_explanation          TEXT NULL,
    stylist_notes           TEXT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at                 TIMESTAMPTZ NULL,
    is_favorite             BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_formula_risk_score CHECK (risk_score BETWEEN 0 AND 1)
);

COMMENT ON TABLE formula IS
    'Brand is derived via formula.line_id -> product_line.brand_id; brand_id is not stored to prevent line/brand drift.';

CREATE INDEX idx_formula_consultation
    ON formula (consultation_id, status);

CREATE TABLE formula_step (
    step_id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id                  UUID NOT NULL REFERENCES formula(formula_id) ON DELETE CASCADE,
    step_order                  INT NOT NULL,
    zone                        formula_zone NOT NULL,
    shade_id                    UUID NULL REFERENCES shade(shade_id) ON DELETE SET NULL,
    developer_id                UUID NULL REFERENCES developer(developer_id) ON DELETE SET NULL,
    mixing_ratio                VARCHAR NULL,
    quantity_grams              INT NULL,
    processing_time_minutes     INT NULL,
    special_instructions        TEXT NULL,
    is_optional                 BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_formula_step_order UNIQUE (formula_id, step_order)
);

CREATE TABLE risk_assessment (
    assessment_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id              UUID NOT NULL REFERENCES formula(formula_id) ON DELETE CASCADE,
    risk_type               risk_type NOT NULL,
    probability             NUMERIC(3, 2) NOT NULL,
    severity                risk_severity NOT NULL,
    contributing_factors    JSONB NOT NULL DEFAULT '[]'::jsonb,
    mitigation              TEXT NOT NULL,
    requires_waiver         BOOLEAN NOT NULL DEFAULT FALSE,
    waiver_text             TEXT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_risk_probability CHECK (probability BETWEEN 0 AND 1)
);

CREATE INDEX idx_risk_assessment_formula
    ON risk_assessment (formula_id, risk_type);

CREATE TABLE formula_outcome (
    outcome_id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    formula_id                      UUID NOT NULL REFERENCES formula(formula_id) ON DELETE RESTRICT,
    actual_result                   TEXT NOT NULL,
    client_satisfaction             INT NOT NULL,
    color_accuracy                  INT NULL,
    condition_after                 INT NULL,
    photos                          TEXT[] NULL,
    corrective_service_needed       BOOLEAN NOT NULL DEFAULT FALSE,
    corrective_service_description  TEXT NULL,
    reported_by                     UUID NULL,
    reported_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_outcome_satisfaction CHECK (client_satisfaction BETWEEN 1 AND 10),
    CONSTRAINT chk_outcome_color_accuracy CHECK (color_accuracy IS NULL OR color_accuracy BETWEEN 1 AND 10),
    CONSTRAINT chk_outcome_condition_after CHECK (condition_after IS NULL OR condition_after BETWEEN 1 AND 10)
);

COMMENT ON COLUMN formula_outcome.reported_by IS 'External stylist/user identity; not FK-enforced.';

-- ---------------------------------------------------------------------------
-- Research-layer index (additive)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_shade_lookup
    ON shade (line_region_id, sub_range_id, shade_code);
