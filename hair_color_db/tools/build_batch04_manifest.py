#!/usr/bin/env python3
"""Generate Batch 4 manifest, sources_used, conflicts, issue_log, package_update_notes."""
import json
import os
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..")
B4 = os.path.join(BASE, "batches", "batch04")
PLAN = json.load(
    open(os.path.join(BASE, "stage03_extraction_plan", "extraction_plan.json"), encoding="utf-8")
)["extraction_plan"]
os.makedirs(B4, exist_ok=True)

SELECTED_SHADE = {
    "Pravana::ChromaSilk VIVIDS Everlasting::US",
    "Pulp Riot::Semi-Permanent::US",
    "Kenra Professional::Kenra Color Permanent::US",
    "Kenra Professional::Kenra Color Demi-Permanent::US",
    "Kenra Professional::Kenra Color Rapid Toners::US",
    "Kenra Professional::Studio Stylist Express::US",
}
LINE_TECH_ONLY = {
    "Kenra Professional::Kenra Color Creatives::US",
    "Paul Mitchell::The Demi::global",
}
JOICO_BLOCK = "source_access_blocked_403"


def reason(entry):
    key = entry["canonical_key"]
    brand = entry["brand_name"]
    if key in SELECTED_SHADE:
        if key.startswith("Kenra"):
            return (
                "Selected — official Kenra Color Wall Chart 2025 / Workbook / SSE manual PDFs "
                "provide machine-readable shade codes (Tier 1)."
            )
        if key == "Pravana::ChromaSilk VIVIDS Everlasting::US":
            return "Selected — deferred from Batch 3; official product pages with JSON-LD (Pravana)."
        if key == "Pulp Riot::Semi-Permanent::US":
            return "Selected — official pulpriothair.com product pages across 6 sub-collections."
    if key in LINE_TECH_ONLY:
        if key == "Paul Mitchell::The Demi::global":
            return (
                "Stage 5 line technical from official paulmitchell.co.th product page. "
                "Shade-level Stage 4 deferred — swatches image-only on official page."
            )
        return (
            "Stage 5 line technical from official landing page. "
            "Shade-level Stage 4 deferred — shade list JS-rendered on /color-list."
        )
    if brand == "Joico":
        return (
            "Deferred — joico.com and direct PDF URLs return HTTP 403 (Cloudflare); "
            "no accessible official distributor PDF located in Batch 4."
        )
    if brand == "Kenra Professional":
        return "Deferred — Batch 4 Kenra quota filled by Permanent/Demi/Rapid Toners/SSE shade extraction."
    if brand == "Paul Mitchell":
        return "Deferred — Batch 4 Paul Mitchell quota filled by The Demi line-tech pass."
    if brand == "Pulp Riot":
        return "Deferred — Batch 4 Pulp Riot quota filled by Semi-Permanent (Paint) extraction."
    if brand == "Pravana" and key == "Pravana::Pure Light::US":
        return "Deferred — lightener line (no shade codes); technical PDF not publicly downloadable."
    return "Deferred — shade_chart_source_not_yet_cataloged per Stage 3 extraction plan."


def blockers(entry):
    key = entry["canonical_key"]
    b = list(entry.get("blockers") or [])
    if key in LINE_TECH_ONLY:
        if key.startswith("Paul Mitchell"):
            b.append("shade_codes_in_image_only_no_text_or_pdf")
        else:
            b.append("shade_list_client_side_rendered")
    if entry["brand_name"] == "Joico":
        b = [JOICO_BLOCK]
    return b


manifest = []
for entry in PLAN:
    if entry["brand_name"] not in (
        "Joico",
        "Kenra Professional",
        "Pravana",
        "Paul Mitchell",
        "Pulp Riot",
    ):
        continue
    manifest.append(
        {
            "canonical_key": entry["canonical_key"],
            "brand_name": entry["brand_name"],
            "product_line_name": entry["product_line_name"],
            "selected_for_batch": entry["canonical_key"] in SELECTED_SHADE
            or entry["canonical_key"] in LINE_TECH_ONLY,
            "primary_extraction_source_url": entry["primary_extraction_source_url"],
            "secondary_source_urls": entry.get("secondary_source_urls") or [],
            "reason_selected_or_deferred": reason(entry),
            "blockers": blockers(entry),
        }
    )

norm = json.load(
    open(os.path.join(B4, "normalized_shade_records_batch_4.json"), encoding="utf-8")
)
shade_count = len(norm["normalized_shade_records"])

sources_used = {
    "source_catalog": [
        {
            "canonical_key": "Pravana::ChromaSilk VIVIDS Everlasting::US",
            "source_title": "PRAVANA ChromaSilk VIVIDS Everlasting product pages",
            "source_type": "official_product_page",
            "source_url": "https://www.pravana.com/products/color/permanent/chromasilk-vivids-everlasting/",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "7 Everlasting shades with JSON-LD Product blocks.",
            "source_priority_tier": 1,
        },
        {
            "canonical_key": "Pulp Riot::Semi-Permanent::US",
            "source_title": "Pulp Riot Semi-Permanent (Paint) sub-collection product pages",
            "source_type": "official_product_page",
            "source_url": "https://www.pulpriothair.com/products/haircolor/semi-permanent-haircolor",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "29 shades across OG Semis, Cosmic, Neon Electric, NeoPop, Impulse, 70s collections.",
            "source_priority_tier": 1,
        },
        {
            "canonical_key": "Kenra Professional::Kenra Color Permanent::US",
            "source_title": "Kenra Color Wall Chart 2025 PDF",
            "source_type": "official_pdf_shade_chart",
            "source_url": "https://kenraprofessional.com/static/713d5a339ba48d85f884841c17542dde/Kenra_Color_Wall_Chart_2025.pdf",
            "publication_or_revision_date": "2025",
            "access_status": "public",
            "coverage_summary": "Permanent + demi shade codes on official wall chart text layer.",
            "source_priority_tier": 1,
        },
        {
            "canonical_key": "Kenra Professional::Studio Stylist Express::US",
            "source_title": "Studio Stylist Express Technical Manual PDF",
            "source_type": "official_pdf_technical_guide",
            "source_url": "https://kenraprofessional.com/static/79c78d5dc48cfbc132fc33166e1a48ee/Studio_Stylist_Express_Color_Manual.pdf",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "17 SSE shades with series legend (N, NB, A, B, G).",
            "source_priority_tier": 1,
        },
        {
            "canonical_key": "Paul Mitchell::The Demi::global",
            "source_title": "Paul Mitchell The Demi official product page (Thailand)",
            "source_type": "official_product_page",
            "source_url": "https://paulmitchell.co.th/en/product/paul-mitchell-the-demi-en/",
            "publication_or_revision_date": None,
            "access_status": "public",
            "coverage_summary": "Line positioning, mixing, processing; shade swatches image-only.",
            "source_priority_tier": 1,
        },
    ],
    "missing_source_targets": [
        "Paul Mitchell The Demi machine-readable shade chart/PDF",
        "Kenra Color Creatives shade list (JS-rendered color-list page)",
        "Joico official shade chart PDF (site blocked)",
        "Remaining Pulp Riot Semi shades beyond 29 verified sub-collection pages",
    ],
    "issue_log": [
        "Kenra permanent/demi shade names default to codes — wall chart PDF lacks display names in text layer.",
        "Paul Mitchell The Demi: line technical only; 65+ shades on image swatches.",
        "Kenra Creatives: line technical only; /color-list?filter=creatives is client-rendered.",
        "Joico: all fetches returned HTTP 403 (unchanged from Batch 3).",
    ],
}

conflicts = []

issue_log = [
    {
        "item": "Joico (all lines)",
        "issue_type": "source_access",
        "details": "joico.com and direct PDF URLs return HTTP 403 from cloud agent environment. Batch 4 retried; no official distributor PDF mirror found.",
    },
    {
        "item": "Paul Mitchell The Demi",
        "issue_type": "shade_extraction_blocked",
        "details": "Official paulmitchell.co.th page publishes shade swatches as images; only 14 numeric codes in HTML metadata.",
    },
    {
        "item": "Kenra Color Creatives",
        "issue_type": "shade_extraction_blocked",
        "details": "Official /color-list?filter=creatives renders shade inventory client-side; no public PDF shade chart cataloged.",
    },
    {
        "item": "Kenra wall chart shade names",
        "issue_type": "partial_metadata",
        "details": "PDF text layer extracts codes reliably but not companion marketing shade names.",
    },
    {
        "item": "Pulp Riot Semi-Permanent coverage",
        "issue_type": "partial_line_coverage",
        "details": "29 shades extracted from 6 sub-collections; official line claims 44+ shades — remaining shades not on crawled collection pages.",
    },
]

package_notes = {
    "artifacts_to_update": {
        "manifest": "hair_color_db/batches/batch04/batch_4_manifest.json",
        "README": "hair_color_db/README.md — add Batch 4 coverage counts",
        "normalized_dataset": "hair_color_db/stage12_package/C_normalized_shade_records.json — append Batch 4 normalized records",
        "raw_append_only_layer": "hair_color_db/batches/batch04/raw_shade_records_batch_4.json",
        "line_technical": "hair_color_db/stage12_package/D_line_technical_records.json — append 8 line records",
        "tone_reference_tables": "hair_color_db/stage12_package/E + F — append Batch 4 tone rows",
        "gap_report_counts": "hair_color_db/stage11_gaps/gap_risk_report.json — update Joico/Kenra/Paul Mitchell/Pulp Riot/Pravana gaps",
        "schema_notes": None,
    },
    "batch_4_summary": {
        "lines_with_shade_extraction": 6,
        "lines_line_technical_only": 2,
        "raw_shade_records_added": shade_count,
        "normalized_shade_records_added": shade_count,
        "brands": ["Pravana", "Pulp Riot", "Kenra Professional", "Paul Mitchell"],
        "joico_status": "all lines still blocked — deferred to Batch 5 pending alternate source access",
    },
    "stage_10_reconsideration": None,
}

json.dump(
    {"batch": 4, "generated": str(date.today()), "batch_4_manifest": manifest},
    open(os.path.join(B4, "batch_4_manifest.json"), "w"),
    indent=2,
    ensure_ascii=False,
)
json.dump(sources_used, open(os.path.join(B4, "batch04_sources_used.json"), "w"), indent=2, ensure_ascii=False)
json.dump(
    {"batch": 4, "source_conflicts": conflicts},
    open(os.path.join(B4, "source_conflicts_batch_4.json"), "w"),
    indent=2,
)
json.dump(
    {"batch": 4, "batch_4_issue_log": issue_log},
    open(os.path.join(B4, "batch_4_issue_log.json"), "w"),
    indent=2,
)
json.dump(
    {"batch": 4, "package_update_notes": package_notes},
    open(os.path.join(B4, "package_update_notes.json"), "w"),
    indent=2,
)
print("manifest entries", len(manifest), "shades", shade_count)
