#!/usr/bin/env python3
"""Build raw Wella shade/line JSON records from manually verified extractions.

Every shade code below was transcribed from text actually extracted (pypdf) from
fetched source documents. No codes are invented. See source constants for URLs.
"""
import json
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- sources
KP_LEAFLET_URL = "https://www.wella.com/professional/m/Shadechart_LP/Wella-Professionals_Koleston-Perfect_Leaflet.pdf"
KP_LEAFLET_DOC = "Koleston Perfect Usage Guidelines leaflet / shade chart (official wella.com PDF)"
KP_BOOKLET_URL = "https://www.wella.com/professional/m/_master/products/koleston_perfect/pdfs/koleston-perfect_usagebooklet.pdf"
KP_BOOKLET_DOC = "Koleston Perfect Technical Folder / usage booklet (official wella.com PDF, older generation)"
KP_FACTSHEET_US_URL = "https://www.wella.com/professional/m/_master/PDF/Products/Koleston_Perfect_Fact_Sheet.pdf"
KP_FACTSHEET_UK_CTF_URL = "https://assets.ctfassets.net/045r8o938mua/gqK2qu91DzPugE5JQwyxn/58d66f3e0d66149fc839c95f0e7f4742/WP_COL_FS.pdf"
KP_SS_GUIDE_URL = "https://www.salon-services.com/on/demandware.static/-/Sites-salon-services-Library/default/dw16da43d0/1-PDF/WELLA-Koleston-Perfect-Technical-Guide.pdf"
KP_RANGE_PAGE_URL = "https://www.wella.com/professional/en-US/koleston-perfect"

CT_LEAFLET_URL = "https://www.wella.com/professional/m/Shadechart_LP/Wella-Professionals_Color-Touch_Leaflet.pdf"
CT_LEAFLET_DOC = "Color Touch Usage Guidelines leaflet / shade chart (official wella.com PDF)"
CT_TECHFOLDER_URL = "https://www.wella.com/professional/m/_master/products/color_touch_NEW/PDFs/Wella_Color_Touch_Technical_Folder.pdf"
CT_TECHFOLDER_DOC = "Wella Color Touch Technical Folder (official wella.com PDF, older generation)"
CT_SS_BROCHURE_URL = "https://www.salon-services.com/on/demandware.static/-/Sites-salon-services-Library/default/dw534f9e2b/brands/wella/color-touch/ct-digital-brochure.pdf"
CT_SS_BROCHURE_DOC = "Color Touch Technical Guide digital brochure (Sally Salon Services distributor PDF)"
CT_FACTSHEET_EN_URL = "https://www.wella.com/professional/m/pdf/FactSheet_EN/ColorTouch/Color_Touch_Fact_Sheet.pdf"
CT_FACTSHEET_UK_URL = "https://www.wella.com/professional/m/pdf/factsheet_uk/WELLA-Color-College_FactSheet_Color_Touch_FINAL.pdf"
CT_US_STORE_URL = "https://us.wella.professionalstore.com/en-US/color-touch"

KP_KEY = "Wella Professionals::Koleston Perfect::US"
CT_KEY = "Wella Professionals::Color Touch::US"

# ------------------------------------------------- Koleston Perfect shades
# Transcribed from the shade matrix pages of the official KP leaflet.
KP_LEAFLET = {
    "Pure Naturals": [
        "10/0", "10/00", "10/03", "10/04",
        "9/0", "99/0", "9/00", "9/01", "9/03", "9/04",
        "8/0", "88/0", "88/02", "8/00", "8/01", "8/03", "8/04", "8/07",
        "7/0", "77/0", "77/02", "7/00", "7/01", "7/03", "7/07",
        "6/0", "66/0", "66/02", "6/00", "6/07",
        "5/0", "55/0", "55/02", "5/00", "5/07",
        "4/0", "44/0", "4/00", "4/07",
        "3/0", "33/0", "3/00",
        "2/0",
    ],
    "Rich Naturals": [
        "10/1", "10/16", "10/3", "10/31", "10/38", "10/8", "10/86", "10/95", "10/96", "10/97",
        "9/1", "9/16", "9/17", "9/3", "9/31", "9/38", "9/8", "9/81", "9/96", "9/97",
        "8/1", "8/2", "8/3", "8/38", "8/96", "8/97",
        "7/1", "7/17", "7/18", "7/3", "7/31", "7/36", "7/37", "7/38",
        "6/1", "6/2", "6/3", "6/91", "6/97",
        "5/1", "5/18", "5/2", "5/3", "5/37",
        "4/3",
        "2/8",
    ],
    "Vibrant Reds": [
        "99/44",
        "8/34", "8/41", "8/43", "88/43", "8/45",
        "7/34", "7/41", "7/43", "77/43", "77/44", "77/46", "7/47",
        "6/34", "6/41", "6/43", "66/44", "6/45", "66/46", "6/5", "66/55", "66/56",
        "5/41", "5/43", "55/46", "5/5", "55/55", "55/65", "55/66",
        "44/44", "44/65",
        "33/55", "33/66",
    ],
    "Special Blonde": [
        "12/0", "12/03", "12/07", "12/1", "12/11", "12/16", "12/22", "12/61", "12/81", "12/89", "12/96",
    ],
    "Special Mix": [
        "0/00", "0/11", "0/28", "0/30", "0/33", "0/43", "0/44", "0/65", "0/66", "0/88",
    ],
    "Deep Browns": [
        "9/7", "9/73",
        "8/7", "8/71", "8/73", "8/74",
        "7/7", "7/71", "7/73", "7/75", "7/77",
        "6/7", "6/71", "6/73", "6/74", "6/75", "6/77",
        "5/7", "5/71", "5/73", "5/75", "5/77",
        "4/71", "4/75", "4/77",
    ],
}

# Codes that appear in the older KP Technical Folder / usage booklet shade
# charts but NOT in the current leaflet matrix above.
KP_BOOKLET_EXTRA = {
    "Pure Naturals": ["11/0", "22/0", "6/03"],
    "Rich Naturals": ["11/1", "66/1", "77/1", "99/1", "7/11", "8/11", "9/11", "7/2", "11/3", "77/3", "88/3"],
    "Vibrant Reds": ["4/4", "5/4", "6/4", "7/4", "8/4", "7/45", "5/46", "8/46", "55/44", "4/6", "44/6", "4/66", "5/66", "44/66", "44/55"],
    "Deep Browns": ["66/7"],
    "Special Blonde": ["12/3", "12/7", "12/17"],
    "Special Mix": ["0/22", "0/45", "0/81"],
}

# ----------------------------------------------------- Color Touch shades
# Transcribed from the shade matrix pages of the official Color Touch leaflet.
CT_LEAFLET = {
    "Pure Naturals": [
        "10/0", "9/0", "8/0", "7/0", "6/0", "5/0", "4/0", "3/0", "2/0",
        "10/01", "9/01",
        "10/03", "9/03", "8/03", "7/03", "5/03",
    ],
    "Rich Naturals": [
        "10/1", "10/3", "10/81",
        "9/3", "9/16", "9/36", "9/86", "9/96", "9/97",
        "8/3", "8/35", "8/38", "8/81",
        "7/1", "7/3", "7/86", "7/89", "7/97",
        "6/3", "6/35", "6/37",
        "5/1", "5/3", "5/37", "5/97",
        "2/8",
    ],
    "Vibrant Reds": [
        "10/34", "10/6",
        "8/41", "8/43",
        "7/4", "7/43", "7/47", "77/45",
        "6/4", "6/45", "6/47", "6/57", "66/44", "66/45",
        "5/4", "5/5", "5/66", "55/54", "55/65",
        "4/5", "4/57", "4/6", "44/65",
        "3/5", "3/66", "3/68",
    ],
    "Deep Browns": [
        "10/73",
        "9/73", "9/75",
        "8/71", "8/73",
        "7/7", "7/71", "7/73", "7/75",
        "6/7", "6/71", "6/73", "6/75", "6/77",
        "5/71", "5/73", "5/75",
        "4/71",
    ],
    "Special Mix": [
        "0/00", "0/34", "0/45", "0/56", "0/68", "0/88",
    ],
}

# Color Touch Plus list as printed in the official Color Touch Technical Folder.
CT_PLUS_TECHFOLDER = [
    "33/06", "44/05", "44/06", "44/07",
    "55/03", "55/04", "55/05", "55/06", "55/07",
    "66/03", "66/04", "66/07",
    "77/03", "77/07",
    "88/03", "88/07",
]

# Extra codes only seen in other fetched sources.
CT_TECHFOLDER_EXTRA = {"Deep Browns": ["4/77"]}
CT_SS_EXTRA_PN = ["10/05", "8/05", "6/05"]  # printed in Pure Naturals chart of distributor brochure
CT_SS_AMBIGUOUS = ["5/02", "5/81"]  # printed repeatedly across several family pages

TONE_LEGEND = [
    {"code": "/1", "meaning": "Ash (blue/green)"},
    {"code": "/2", "meaning": "Matt (green)"},
    {"code": "/3", "meaning": "Gold (yellow)"},
    {"code": "/4", "meaning": "Red (warm)"},
    {"code": "/5", "meaning": "Mahogany (red/violet)"},
    {"code": "/6", "meaning": "Violet (cool)"},
    {"code": "/7", "meaning": "Brown (red, yellow, blue)"},
    {"code": "/8", "meaning": "Pearl (blue)"},
    {"code": "/9", "meaning": "Cendre (blue/violet)"},
]

CT_DEPTH_LEGEND = [
    {"code": "10/", "meaning": "Lightest Blonde"},
    {"code": "9/", "meaning": "Very Light Blonde"},
    {"code": "8/", "meaning": "Light Blonde"},
    {"code": "7/", "meaning": "Medium Blonde"},
    {"code": "6/", "meaning": "Dark Blonde"},
    {"code": "5/", "meaning": "Light Brown"},
    {"code": "4/", "meaning": "Medium Brown"},
    {"code": "3/", "meaning": "Dark Brown"},
    {"code": "2/", "meaning": "Black"},
]


def base_record(key, line, code, family, url, doc, stype, confidence, status):
    level, tone = code.split("/")
    return {
        "canonical_key": key,
        "brand": "Wella Professionals",
        "product_line": line,
        "shade_code": code,
        "shade_name": None,
        "level": level,
        "manufacturer_tone_codes": ["/" + tone],
        "manufacturer_tone_descriptions": [],
        "color_type": "permanent" if line == "Koleston Perfect" else "demi-permanent",
        "gray_coverage_claim": None,
        "lift_capability": None,
        "mixing_ratio": None,
        "developer_recommendations": [],
        "processing_time_minutes": None,
        "special_usage_notes": "Listed under the %s family in the source shade chart." % family,
        "official_swatch_image_exists": None,
        "region_or_market": None,
        "source_url": url,
        "source_document": doc,
        "source_type": stype,
        "source_publication_date": None,
        "source_confidence": confidence,
        "evidence_status": status,
        "assumptions": [],
        "data_gaps": [
            "Shade name not printed as extractable text in source document.",
            "Source PDF does not state publication date or target market/region.",
            "Swatch images present in PDF but per-shade swatch existence not verifiable from extracted text (official_swatch_image_exists left null).",
        ],
    }


records = []

# --- Koleston Perfect: current leaflet matrix
for family, codes in KP_LEAFLET.items():
    for code in codes:
        r = base_record(KP_KEY, "Koleston Perfect", code, family,
                        KP_LEAFLET_URL, KP_LEAFLET_DOC, "official_brand_pdf",
                        "high", "confirmed")
        if family == "Special Blonde":
            r["mixing_ratio"] = "1:2 (Koleston Perfect Special Blonde : Welloxon Perfect)"
            r["lift_capability"] = "12% Welloxon Perfect: 4-5 levels of lift; 9% Welloxon Perfect: 3 levels of lift (stated for Special Blonde family)"
            r["developer_recommendations"] = ["Welloxon Perfect 9%", "Welloxon Perfect 12%"]
            r["special_usage_notes"] += " Special Blonde development time per leaflet: 50-60 min without heat, 25-35 min with Climazon."
        if family == "Special Mix":
            r["mixing_ratio"] = ("1:2 with Welloxon Perfect (stated exception for Special Mix 0/43)" if code == "0/43"
                                 else "1:1 with Welloxon Perfect (rule stated for all Special Mix shades except 0/43)")
            r["special_usage_notes"] += " Leaflet: 'Koleston Perfect Special Mix tones are pure color. The lighter the shade, the less mix tone is needed. Exception: Level 12/.'"
        records.append(r)

# --- Koleston Perfect: extra codes only in older booklet
for family, codes in KP_BOOKLET_EXTRA.items():
    for code in codes:
        r = base_record(KP_KEY, "Koleston Perfect", code, family,
                        KP_BOOKLET_URL, KP_BOOKLET_DOC, "official_brand_pdf",
                        "medium", "partially_confirmed")
        r["assumptions"].append("Code appears only in the older Koleston Perfect Technical Folder shade chart, not in the current official leaflet matrix; may have been discontinued or renumbered.")
        r["data_gaps"].append("Not present in current official leaflet shade matrix; current availability unverified.")
        if code in ("66/1", "77/1", "99/1", "77/3", "88/3"):
            r["source_confidence"] = "low"
            r["assumptions"].append("Multi-column PDF chart was text-extracted; double-digit code may be a column-merge artifact of extraction.")
        if family == "Special Blonde":
            r["mixing_ratio"] = "1:2 (Koleston Perfect Special Blonde : Welloxon Perfect)"
        if family == "Special Mix":
            r["mixing_ratio"] = "1:1 with Welloxon Perfect (rule stated for all Special Mix shades except 0/43)"
        records.append(r)

# --- Color Touch: current leaflet matrix
for family, codes in CT_LEAFLET.items():
    for code in codes:
        r = base_record(CT_KEY, "Color Touch", code, family,
                        CT_LEAFLET_URL, CT_LEAFLET_DOC, "official_brand_pdf",
                        "high", "confirmed")
        if family == "Special Mix":
            r["special_usage_notes"] += (" Leaflet Special Mix uses: Pure (e.g. 20g Special Mix + 40g 1.9%/4%); Pastelization with 0/00; "
                                         "Boost with 0/56; Correct with 0/68.")
        records.append(r)

# --- Color Touch Plus from official technical folder
for code in CT_PLUS_TECHFOLDER:
    r = base_record(CT_KEY, "Color Touch", code, "Color Touch Plus",
                    CT_TECHFOLDER_URL, CT_TECHFOLDER_DOC, "official_brand_pdf",
                    "high", "confirmed")
    r["mixing_ratio"] = "1:2 (Color Touch Plus : Color Touch Plus Emulsion 4%)"
    r["developer_recommendations"] = ["Color Touch Plus Emulsion 4%"]
    r["gray_coverage_claim"] = "Up to 70% gray coverage (stated for the Color Touch Plus sub-range, not per shade)"
    r["special_usage_notes"] += " Technical folder: 'MIX WITH COLOR TOUCH EMULSION 4%'. Current leaflet also shows a Plus matrix (column headers X/03 X/04 X/05 X/06 X/07) but its extracted values were garbled; this list is taken from the technical folder."
    records.append(r)

# --- Color Touch extras
for family, codes in CT_TECHFOLDER_EXTRA.items():
    for code in codes:
        r = base_record(CT_KEY, "Color Touch", code, family,
                        CT_TECHFOLDER_URL, CT_TECHFOLDER_DOC, "official_brand_pdf",
                        "medium", "partially_confirmed")
        r["assumptions"].append("Code appears only in the older Color Touch Technical Folder chart, not in the current leaflet matrix.")
        r["data_gaps"].append("Not present in current official leaflet shade matrix; current availability unverified.")
        records.append(r)

for code in CT_SS_EXTRA_PN:
    r = base_record(CT_KEY, "Color Touch", code, "Pure Naturals",
                    CT_SS_BROCHURE_URL, CT_SS_BROCHURE_DOC, "distributor_pdf",
                    "high", "confirmed")
    if code in ("6/05", "8/05"):
        r["assumptions"].append("Also corroborated by formulas printed on the official US store page (%s)." % CT_US_STORE_URL)
        r["region_or_market"] = "US (corroborated on us.wella.professionalstore.com)"
    records.append(r)

for code in CT_SS_AMBIGUOUS:
    r = base_record(CT_KEY, "Color Touch", code, "uncertain (code printed on multiple family pages)",
                    CT_SS_BROCHURE_URL, CT_SS_BROCHURE_DOC, "distributor_pdf",
                    "low", "partially_confirmed")
    r["special_usage_notes"] = None
    r["assumptions"].append("Code string appears repeatedly across several shade-family pages of the extracted brochure text; likely a 'NEW shade' callout repeated per page, so the owning family could not be determined.")
    r["data_gaps"].append("Shade family placement ambiguous; code not present in official leaflet matrix; could be a text-extraction artifact.")
    records.append(r)

source_conflicts = [
    {
        "canonical_key": KP_KEY, "shade_code": None,
        "field_name": "processing_time_with_heat (standard shades)",
        "conflicting_values": [
            "15-25 min with heat (official leaflet and usage booklet)",
            "15-20 min with heat (Koleston_Perfect_Fact_Sheet.pdf, US factsheet)",
        ],
        "preferred_value": "15-25 min with heat",
        "reason": "Leaflet and technical folder are the more detailed, current usage documents; factsheet appears older.",
    },
    {
        "canonical_key": KP_KEY, "shade_code": None,
        "field_name": "Special Blonde lift per developer strength",
        "conflicting_values": [
            "12% = 4-5 levels, 9% = 3 levels (official leaflet and US factsheet)",
            "12% = 5 levels, 9% = 4 levels, 6% = 3 levels (UK Colour Brand Factsheet on assets.ctfassets.net, WP_COL_FS.pdf)",
        ],
        "preferred_value": "12% = 4-5 levels, 9% = 3 levels",
        "reason": "Matches the current official leaflet; UK factsheet may reflect a different market/version.",
    },
    {
        "canonical_key": KP_KEY, "shade_code": None,
        "field_name": "total shade count claim",
        "conflicting_values": [
            "140+ shades (official US range page, wella.com/professional/en-US/koleston-perfect)",
            "more than 160 shades (older Technical Folder usage booklet)",
            "100+ unique shades (salon-services Koleston Perfect Technical Guide)",
        ],
        "preferred_value": "140+ shades (US market claim)",
        "reason": "Canonical key is the US market; the US range page is the current official US source. Counts likely differ by market and document generation.",
    },
    {
        "canonical_key": CT_KEY, "shade_code": None,
        "field_name": "color longevity (washes/shampoos)",
        "conflicting_values": [
            "lasts up to 15 shampoos (UK factsheet WELLA-Color-College_FactSheet_Color_Touch_FINAL.pdf)",
            "lasts up to 24 shampoos (EN factsheet Color_Touch_Fact_Sheet.pdf)",
            "beautifully fades over 28 washes (official US store page); lasts up to 28 washes (distributor technical guide, stated for blonde toning)",
        ],
        "preferred_value": "fades over 28 washes",
        "reason": "US store page is the current official US-market source; lower figures come from older factsheets/formulations.",
    },
    {
        "canonical_key": CT_KEY, "shade_code": None,
        "field_name": "ammonia-free claim scope",
        "conflicting_values": [
            "Ammonia free: COLOR TOUCH, Sunlights (except Sunlight/0) and Relights (technical folder/factsheets)",
            "Ammonia Free Formula except Color Touch Plus which is low-ammonia (US store page); Plus 'contains both MEA and low-ammonia' (distributor guide)",
        ],
        "preferred_value": "Core Color Touch ammonia-free; Color Touch Plus low-ammonia",
        "reason": "Statements are consistent once Plus is treated separately; recorded as scope clarification rather than true contradiction.",
    },
]

issue_log = [
    "Provided URL https://www.wella.com/professional/m/_master/products/koleston_perfect/pdfs/koleston-perfect-me-usage-instructions.pdf returned HTTP 404 (HTML error page, no %PDF header); replaced with koleston-perfect_usagebooklet.pdf found via search.",
    "Koleston Perfect shade roster taken from the official leaflet shade matrix (168 codes). The current official US range page claims '140+ shades' but does not enumerate them, so the leaflet matrix may include shades not sold in the US; per-shade US availability not verified.",
    "Older KP Technical Folder contributed extra codes not in the current leaflet (recorded as partially_confirmed). Its multi-column charts were text-extracted; codes 66/1, 77/1, 99/1, 77/3, 88/3 flagged low confidence as possible column-merge artifacts.",
    "KP booklet chart also printed level-11 codes (11/0, 11/1, 11/3) which are absent from the current leaflet.",
    "Color Touch official leaflet's Color Touch Plus matrix extracted as garbled/repeated values; the Plus roster was instead taken from the official Color Touch Technical Folder (16 codes).",
    "Color Touch sub-ranges Relights, Sunlights and iNSTAMAT!C by Color Touch were observed in the technical folder (e.g. Relights /00, /03, /06, /18, /34, /43, /44, /47, /56, /57, /74, /86; iNSTAMAT!C named shades Ocean Storm, Pink Dream, Muted Mauve, Smokey Amethyst, Jaded Mint, Clear Dust) but were NOT emitted as core shade records; they use slash-only or name-based codes outside the core numbering.",
    "us.wella.professionalstore.com Color Touch page fetched successfully but its 'shop by shade family' tiles did not render as enumerable text; only shade codes embedded in look formulas were corroborated from it. Full US store shade enumeration is a completeness gap.",
    "SalonCentric was not consulted (known bot-blocking; task allowed skipping).",
    "Wella Color Touch is claimed as a '77 shade' portfolio on an official wella.com market page (jp-JP, seen in search results); the leaflet matrix plus Plus and distributor extras recorded here total ~115 codes across document generations - counts differ by market and generation.",
    "No per-shade names, gray-coverage claims, or per-shade processing times are printed in any fetched source; those fields are null at shade level by design.",
    "No source PDF carries an extractable publication date; source_publication_date is null throughout.",
]

shade_file = {
    "raw_shade_records": records,
    "source_conflicts": source_conflicts,
    "issue_log": issue_log,
}

# ---------------------------------------------------------------- line file
kp_line = {
    "canonical_key": KP_KEY,
    "brand": "Wella Professionals",
    "product_line": "Koleston Perfect",
    "color_type": "permanent",
    "default_mixing_ratio": "1:1 with Welloxon Perfect (Pure Naturals, Rich Naturals, Vibrant Reds, Deep Browns); 1:2 for Special Blonde; Special Mix 1:1 except 0/43 at 1:2",
    "developer_options": [
        "Welloxon Perfect Pastel 1.9%",
        "Welloxon Perfect 4%",
        "Welloxon Perfect 6%",
        "Welloxon Perfect 9%",
        "Welloxon Perfect 12%",
    ],
    "developer_strengths_if_stated": [
        "1.9% (6 Vol) - for color balancing, blonde toning and glossing services",
        "4% (13 Vol) - same depth or darker; deeper results on natural hair with no grey coverage required",
        "6% (20 Vol) - 1 level of lift; coverage of grey hair; same depth or darker",
        "9% (30 Vol) - 2 levels of lift; 3 levels with Special Blonde",
        "12% (40 Vol) - 3 levels of lift; 4-5 levels with Special Blonde",
    ],
    "processing_time_ranges": [
        "Standard shades (Pure Naturals/Rich Naturals/Vibrant Reds/Deep Browns): 30-40 min without heat; 15-25 min with heat (Climazon)",
        "Special Blonde: 50-60 min without heat; 25-35 min with heat",
        "Full-head application with lightening, step 1 (lengths and ends): 20 min without heat / 10 min with heat (Pure Naturals/Rich Naturals/Deep Browns)",
        "Pastel toning: up to 15 min without heat, combing every 5 min",
        "Color leveling on lengths and ends: 5-10 min without heat",
        "Glossing (Welloxon Perfect Pastel 1.9%): 5-15 min",
        "Intense Balance: apply to lengths for last 10-15 min of root development",
    ],
    "gray_coverage_rules": [
        "Up to 100% coverage of grey/white hair (official factsheets and US range page)",
        "Use 6% Welloxon Perfect for coverage of grey/white hair",
        "30-50% grey hair: add 1/3 of a Pure Naturals shade (e.g. 15g 7/0 + 45g 7/75 + 60g 6%)",
        "50-100% grey hair: add 1/2 of a Pure Naturals shade (e.g. 30g 7/0 + 30g 7/75 + 60g 6%)",
        "Red shades on white hair with more than 50% white: mix 2 parts red shade to 1 part Pure Natural (older booklet)",
        "Coloring grey hair: the addition of a Pure Naturals shade is required to give sufficient grey coverage; for resistant hair use the resistant cover shade (xx/0) as the natural shade (distributor technical guide); maximum development 40 min for grey coverage (distributor technical guide)",
    ],
    "lift_rules": [
        "12% Welloxon Perfect for 3 levels of lift (standard shades)",
        "9% Welloxon Perfect for 2 levels of lift (standard shades)",
        "6% Welloxon Perfect for 1 level of lift",
        "Special Blonde: 12% for 4-5 levels of lift, 9% for 3 levels of lift (1:2 mix)",
        "Up to 100% grey coverage, up to 5 levels of lift (booklet benefit claim)",
    ],
    "tone_family_legend": TONE_LEGEND,
    "special_usage_notes": [
        "Shade numbering system stated in official Technical Folder: position 1 = Depth of color; position 2 = Major tone of color; position 3 = Minor tone of color (example printed: 4/71).",
        "Color families printed in sources: Pure Naturals, Rich Naturals, Vibrant Reds, Deep Browns, Special Blonde, Special Mix.",
        "Special Mix shades are pure color tones; the lighter the basic shade, the less mix tone is needed (exception: levels 11 and 12 per booklet; 'Exception: Level 12/' per leaflet). Mixing ratio 1:1 for all Special Mix except 0/43 (1:2).",
        "Pastel toning: evenly pre-lightened hair required (1/2 level lighter than final result); recommended shades 10/1 10/03 10/16 10/3 10/38 10/8 9/03 9/16 9/17 9/38 9/7; mix 1:2 with Color Touch Emulsion 1.9% or Welloxon Perfect Pastel.",
        "Allergy Alert Test recommended 48 hours before coloring (all sources).",
        "ME+ dye technology replaces PTD and PPD to reduce risk of developing new allergy (factsheets, US range page); Metal Purifier technology integrated (US range page, distributor guide).",
        "After treatment: emulsify with warm water, rinse, shampoo (Invigo Color Brilliance per leaflet), then Color Service Post Color Treatment to neutralize oxidation residues.",
    ],
    "region_or_market": "US (canonical); leaflet/booklet PDFs are official wella.com documents without an explicit market statement",
    "discontinued_status": "Active - official US range page live as of June 2026",
    "source_url": KP_LEAFLET_URL,
    "source_document": KP_LEAFLET_DOC,
    "source_confidence": "high",
    "evidence_status": "confirmed",
    "assumptions": [
        "Line-level data aggregated from multiple official sources; primary = leaflet. Supplementary: " + "; ".join([
            KP_BOOKLET_URL, KP_FACTSHEET_US_URL, KP_FACTSHEET_UK_CTF_URL, KP_SS_GUIDE_URL, KP_RANGE_PAGE_URL]),
        "Tone legend transcribed verbatim from the official Technical Folder (usage booklet) 'Tone Numbering System' page.",
    ],
    "data_gaps": [
        "No publication dates printed in source PDFs.",
        "US-specific shade availability not enumerated by any fetched US source.",
        "Welloxon Perfect Pastel 1.9% appears in factsheets and leaflet services but exact product naming varies across documents ('Welloxon Perfect Pastel', 'Welloxon Perfect 1.9%').",
    ],
}

ct_line = {
    "canonical_key": CT_KEY,
    "brand": "Wella Professionals",
    "product_line": "Color Touch",
    "color_type": "demi-permanent",
    "default_mixing_ratio": "1:2 (1 part Color Touch + 2 parts Color Touch Emulsion 1.9% or 4%); Color Touch Plus 1:2 with Color Touch Plus Emulsion 4%; iNSTAMAT!C 1:1; Special Mix used within 1:2 total mix",
    "developer_options": [
        "Color Touch Emulsion 1.9%",
        "Color Touch Emulsion 4%",
        "Color Touch Plus Emulsion 4% (for Color Touch Plus only)",
    ],
    "developer_strengths_if_stated": [
        "1.9% (6 vol per US store formulas) - same depth or darkening with soft regrowth; toning blondes; soft grey blending; after perm/straightening",
        "4% - increased colour vibrancy; colouring coarse hair types; intense grey blending; up to 70% grey coverage with Plus; low lift",
    ],
    "processing_time_ranges": [
        "20 min without heat; 15 min with heat (Climazon) - core Color Touch and Color Touch Plus",
        "Blonde toning: 5-20 min, visually develop until desired result (distributor guide)",
        "Relights: blonde shades 5-10 min without heat; red shades 15-20 min without heat (technical folder)",
        "iNSTAMAT!C: 5-20 min depending on intensity, without heat (technical folder)",
        "Color balancing: watch for visual development 5-15 min (technical folder)",
    ],
    "gray_coverage_rules": [
        "Up to 50% grey/white coverage (core Color Touch, factsheets and technical folder)",
        "First-time application ideal for up to 50% grey blending (leaflet)",
        "Up to 70% grey coverage with Color Touch Plus (leaflet, factsheets, US store page, distributor guide)",
        "Color Touch Plus: apply to dry hair for maximum intensity and coverage; for touch-ups start at the roots",
    ],
    "lift_rules": [
        "Demi-permanent; positioned for same depth or darkening / toning (leaflet, distributor guide)",
        "4% emulsion described as 'low lift' (distributor guide); no level-lift claims stated for core Color Touch in fetched sources",
    ],
    "tone_family_legend": TONE_LEGEND + CT_DEPTH_LEGEND,
    "special_usage_notes": [
        "Shade numbering system stated in official Technical Folder: 1 = Depth of color, 2 = Major tone of color, 3 = Minor tone of color (example printed: 4/71). Leaflet: 'depth or base of a color from 2/ - 10/ and the tone from /0 - /9'.",
        "Tone legend transcribed from official Color Touch Technical Folder; the distributor brochure prints slightly different wording (Ash (grey), Matte (green), Gold (yellow), Red (warm), Mahogony, Violet (cool), Brown (warm), Pearl (blue), Cendre (soft violet)); depth legend (2/ Black ... 10/ Lightest Blonde) from distributor brochure.",
        "Special Mix uses (leaflet): Pure over natural or pre-lightened hair (20g Special Mix + 40g emulsion); Pastelization - dilute any shade with 0/00; Boost - intensify with e.g. 0/56; Correct - neutralize warmth with e.g. 0/68; reduce intensity with clear tone 0/00.",
        "Ammonia free: Color Touch, Color Touch Sunlights (except Sunlight/0) and Color Touch Relights; Color Touch Plus is low-ammonia with MEA (US store page, distributor guide).",
        "Upgraded formula (current generation): vegan, silicone free, mineral oil free, built-in Metal Purifier (US store page, distributor guide).",
        "Apply to pre-shampooed, towel-dried hair from roots to ends (first-time application); Plus applied to dry hair.",
        "Sub-ranges observed but not recorded as core shades: Color Touch Relights, Color Touch Sunlights, iNSTAMAT!C by Color Touch.",
        "Allergy Alert Test recommended 48 hours before coloring (all sources).",
        "Longevity claims: fades over 28 washes (US store page, current); older factsheets state up to 24 (EN) / 15 (UK) shampoos - see source_conflicts in the shade file.",
    ],
    "region_or_market": "US (canonical; US store page fetched); leaflet/technical folder are official wella.com documents without explicit market statement; distributor brochure is UK",
    "discontinued_status": "Active - official US store page live as of June 2026",
    "source_url": CT_LEAFLET_URL,
    "source_document": CT_LEAFLET_DOC,
    "source_confidence": "high",
    "evidence_status": "confirmed",
    "assumptions": [
        "Line-level data aggregated from multiple sources; primary = leaflet. Supplementary: " + "; ".join([
            CT_TECHFOLDER_URL, CT_SS_BROCHURE_URL, CT_FACTSHEET_EN_URL, CT_FACTSHEET_UK_URL, CT_US_STORE_URL]),
    ],
    "data_gaps": [
        "No publication dates printed in source PDFs.",
        "US store page did not enumerate the full US shade roster as extractable text.",
        "Official '77 shades' portfolio claim (wella.com jp-JP market page seen in search results) could not be reconciled with the leaflet matrix count.",
    ],
}

line_file = {
    "line_technical_records": [kp_line, ct_line],
    "issue_log": [
        "Koleston Perfect line rules merged from leaflet (primary), older technical folder, US factsheet, UK Contentful factsheet, distributor technical guide and official US range page; conflicts recorded in the shade file's source_conflicts.",
        "Color Touch line rules merged from leaflet (primary), technical folder, EN/UK factsheets, distributor brochure and US store page.",
        "Developer 'vol' equivalences for Koleston Perfect taken verbatim from the leaflet (1.9%=6 Vol, 4%=13 Vol, 6%=20 Vol, 9%=30 Vol, 12%=40 Vol); Color Touch 1.9%=6 vol from US store page formula annotations.",
        "Tone-digit system (first digit after slash = major/primary tone, second = minor/secondary tone) is stated in both official technical folders and recorded in special_usage_notes/tone_family_legend with sources.",
    ],
}

with open(os.path.join(OUT_DIR, "wella_raw_shade_records.json"), "w") as f:
    json.dump(shade_file, f, indent=2, ensure_ascii=False)
with open(os.path.join(OUT_DIR, "wella_line_technical_records.json"), "w") as f:
    json.dump(line_file, f, indent=2, ensure_ascii=False)

kp_n = sum(1 for r in records if r["product_line"] == "Koleston Perfect")
ct_n = sum(1 for r in records if r["product_line"] == "Color Touch")
codes_kp = [r["shade_code"] for r in records if r["product_line"] == "Koleston Perfect"]
codes_ct = [r["shade_code"] for r in records if r["product_line"] == "Color Touch"]
assert len(set(codes_kp)) == len(codes_kp), "duplicate KP codes"
assert len(set(codes_ct)) == len(codes_ct), "duplicate CT codes"
print("KP records:", kp_n, "CT records:", ct_n, "total:", len(records))
