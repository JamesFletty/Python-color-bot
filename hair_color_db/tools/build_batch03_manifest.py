#!/usr/bin/env python3
"""Generate Batch 3 manifest, sources_used, conflicts, issue_log, package_update_notes."""
import json, os
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), '..')
B3 = os.path.join(BASE, 'batches', 'batch03')
PLAN = json.load(open(os.path.join(BASE, 'stage03_extraction_plan', 'extraction_plan.json')))['extraction_plan']
os.makedirs(B3, exist_ok=True)

SELECTED = {
    'Pravana::ChromaSilk Creme Color::US', 'Pravana::ChromaSilk Express Tones::US', 'Pravana::ChromaSilk VIVIDS::US',
    'Goldwell::Topchic::US', 'Goldwell::Colorance::US',
}
GOLDWELL_TECH_ONLY = {'Goldwell::Topchic::US', 'Goldwell::Colorance::US'}
JOICO_BLOCK = 'source_access_blocked_403'

def reason(entry):
    key = entry['canonical_key']
    if key in SELECTED and key in GOLDWELL_TECH_ONLY:
        return 'Stage 5 line technical extracted from official Color Guide HTML. Shade-level Stage 4 deferred — palettes are JPEG swatch charts only.'
    if key in SELECTED:
        return 'Selected — official product pages provide shade-level JSON-LD with mixing, processing, and tone family text (Pravana).'
    if entry['brand_name'] == 'Joico':
        return 'Deferred — joico.com returns HTTP 403 (Cloudflare) from this environment; no accessible official PDF located.'
    if entry['brand_name'] == 'Goldwell':
        return 'Deferred — no machine-readable shade chart/PDF cataloged; Batch 3 Goldwell quota filled by Topchic/Colorance line-tech pass.'
    if key == 'Pravana::ChromaSilk VIVIDS Everlasting::US':
        return 'Deferred — 7 shades on product pages but Batch 3 Pravana line limit reached; PKG PDF pro-gated.'
    if key == 'Pravana::Pure Light::US':
        return 'Deferred — lightener line (no shade codes); technical PDF not publicly downloadable.'
    return 'Deferred — shade_chart_source_not_yet_cataloged per Stage 3 extraction plan.'

def blockers(entry):
    key = entry['canonical_key']
    b = list(entry.get('blockers') or [])
    if key in GOLDWELL_TECH_ONLY:
        b.append('shade_codes_in_image_only_no_text_or_pdf')
    if entry['brand_name'] == 'Joico':
        b = ['source_access_blocked_403']
    if key == 'Goldwell::Topchic Zero::US':
        b.append('line_page_404')
    if key == 'Pravana::ChromaSilk VIVIDS Everlasting::US' and key not in SELECTED:
        b.append('batch_line_limit')
    return b

manifest = []
for entry in PLAN:
    if entry['brand_name'] not in ('Goldwell', 'Joico', 'Pravana'):
        continue
    manifest.append({
        'canonical_key': entry['canonical_key'],
        'brand_name': entry['brand_name'],
        'product_line_name': entry['product_line_name'],
        'selected_for_batch': entry['canonical_key'] in SELECTED,
        'primary_extraction_source_url': entry['primary_extraction_source_url'],
        'secondary_source_urls': entry.get('secondary_source_urls') or [],
        'reason_selected_or_deferred': reason(entry),
        'blockers': blockers(entry),
    })

sources_used = {
    "source_catalog": [
        {
            "canonical_key": "Pravana::ChromaSilk Creme Color::US",
            "source_title": "PRAVANA Color category + individual ChromaSilk Crème Color product pages",
            "source_type": "official_product_page",
            "source_url": "https://www.pravana.com/products/color/",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "84 permanent shades with JSON-LD Product blocks (name, description, How To Use, Features, images).",
            "source_priority_tier": 1,
        },
        {
            "canonical_key": "Goldwell::Topchic::US",
            "source_title": "Goldwell US Color Guide — Topchic section",
            "source_type": "official_education_page",
            "source_url": "https://www.goldwell.com/en-us/education/color-guide1/topchic/",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "Developer/lift/gray-coverage HTML tables + JPEG palette images (4-topchic-s24-b1.jpg … s28-b6.jpg).",
            "source_priority_tier": 1,
        },
    ],
    "missing_source_targets": [
        "Goldwell Topchic/Colorance machine-readable shade chart PDF",
        "Joico official shade chart PDF (site blocked)",
        "Pravana Product Knowledge Guide PDF (pro-gated flipbook)",
    ],
    "issue_log": [
        "Pravana shades extracted from official product pages (not PDF) — JSON-LD + meta descriptions.",
        "Goldwell shade palettes are image-only on Color Guide; line technical only for Batch 3.",
        "Joico: all fetches returned HTTP 403.",
    ],
}

conflicts = []

issue_log = [
    {"item": "Joico (all lines)", "issue_type": "source_access", "details": "joico.com returns HTTP 403 from cloud agent environment (Cloudflare). No official PDF mirror found on CosmoProf/SalonCentric."},
    {"item": "Goldwell Topchic/Colorance", "issue_type": "shade_extraction_blocked", "details": "Official Color Guide publishes palette JPEGs on Adobe DAM without extractable shade codes or companion PDF."},
    {"item": "Pravana Product Knowledge Guide", "issue_type": "pro_gated_pdf", "details": "Full digit tone legend lives in pro-gated flipbook at /pro/product-knowledge-guide/; combo-code mappings derived from public product page descriptions instead."},
    {"item": "Pravana shade_code vs SKU", "issue_type": "schema_convention", "details": "WooCommerce SKU (internal) explicitly not used as shade_code; manufacturer-facing codes taken from URL slug / printed product name."},
    {"item": "Goldwell Topchic Zero", "issue_type": "stale_url", "details": "color-guide1/topchic-zero/ returned 404 during Batch 3 fetch."},
]

package_notes = {
    "artifacts_to_update": {
        "manifest": "hair_color_db/batches/batch03/batch_3_manifest.json — new Batch 3 line selection record",
        "README": "hair_color_db/README.md — add Batch 3 coverage counts (139 new shades, 3 Pravana lines + 2 Goldwell line-tech)",
        "normalized_dataset": "hair_color_db/stage12_package/C_normalized_shade_records.json — append 139 Pravana normalized records (Stage 12 regen)",
        "raw_append_only_layer": "hair_color_db/batches/batch03/pravana_raw_shade_records.json",
        "line_technical": "hair_color_db/stage12_package/D_line_technical_records.json — append 5 line records (3 Pravana + 2 Goldwell)",
        "tone_reference_tables": "hair_color_db/stage12_package/E_manufacturer_tone_reference.json + F_tone_normalization_map.json",
        "gap_report_counts": "hair_color_db/stage11_gaps/gap_risk_report.json — decrement open gaps for 3 Pravana lines; Joico/Goldwell shade gaps remain",
        "schema_notes": None
    },
    "batch_3_summary": {
        "lines_with_shade_extraction": 3,
        "lines_line_technical_only": 2,
        "raw_shade_records_added": 139,
        "normalized_shade_records_added": 139,
        "brands": ["Pravana", "Goldwell"],
        "joico_status": "all lines blocked — deferred to Batch 4 pending source access"
    },
    "stage_10_reconsideration": None
}

json.dump({"batch": 3, "generated": str(date.today()), "batch_3_manifest": manifest},
          open(os.path.join(B3, 'batch_3_manifest.json'), 'w'), indent=2, ensure_ascii=False)
json.dump(sources_used, open(os.path.join(B3, 'batch03_sources_used.json'), 'w'), indent=2, ensure_ascii=False)
json.dump({"batch": 3, "source_conflicts": conflicts}, open(os.path.join(B3, 'source_conflicts_batch_3.json'), 'w'), indent=2)
json.dump({"batch": 3, "batch_3_issue_log": issue_log}, open(os.path.join(B3, 'batch_3_issue_log.json'), 'w'), indent=2)
json.dump({"batch": 3, "package_update_notes": package_notes}, open(os.path.join(B3, 'package_update_notes.json'), 'w'), indent=2)
print('manifest entries', len(manifest))
