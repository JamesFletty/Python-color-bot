-- =============================================================================
-- Matrix SoColor (US) shade intermixing rule seeds.
--
-- These INSERTs are data-dependent: they SELECT from the research tables
-- (brand / product_line / product_line_region / sub_range / source_document),
-- so they MUST run AFTER the Stage 12 research import has populated those
-- tables. They previously lived in production_operational_schema.sql and ran
-- during migration (before any research data existed), so every SELECT matched
-- zero rows and no intermixing rules were ever loaded.
--
-- Applied by hair_color_db.production.import_stage12_research.import_intermixing_rules().
-- Idempotent: existing Matrix SoColor (US) rules are cleared before re-seeding.
-- =============================================================================

DELETE FROM shade_intermixing_rule
WHERE line_region_id IN (
    SELECT plr.line_region_id
    FROM product_line_region plr
    JOIN product_line pl ON pl.line_id = plr.line_id
    JOIN brand b ON b.brand_id = pl.brand_id
    WHERE b.brand_name = 'Matrix'
      AND pl.product_line_name ILIKE '%SoColor%'
      AND pl.product_line_name NOT ILIKE '%Sync%'
      AND plr.region_or_market = 'US'
);

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
