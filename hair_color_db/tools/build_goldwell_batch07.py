#!/usr/bin/env python3
"""Build Goldwell Topchic and Colorance shade records (Stages 4-8).

Primary machine-readable sources (official Goldwell/Kao PDFs):
  - Topchic palette: Product Book 2018, printed shade grid p.17 (PDF page index 9)
  - Topchic/Colorance matrix + Colorance coverage: Color Continuum 2020, p.69
  - Mix additives: Color Continuum ch.7 p.58 (Topchic), ch.10 p.101 (Colorance)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

BASE = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(BASE, "batches", "batch07")

PRODUCT_BOOK_URL = (
    "https://www.goldwell.com/content/dam/sites/kaousa/www-goldwell-com/"
    "content/dk/da_dk/pdf/180125-kao-gw-product-book-2018-pages-web.compressed.pdf"
)
CONTINUUM_URL = (
    "https://www.goldwell.com/content/dam/sites/kaousa/www-goldwell-com/content/us/en_us/pdf/"
    "KEDU_1943539%202020%20Color%20Continuum%20%28All%20About%20Color%29_FINAL.pdf"
)
COLOR_GUIDE_TOPCHIC_URL = "https://www.goldwell.com/en-us/education/color-guide1/topchic/"
COLOR_GUIDE_COLORANCE_URL = "https://www.goldwell.com/en-us/education/color-guide1/colorance/"

TOPCHIC_KEY = "Goldwell::Topchic::US"
COLORANCE_KEY = "Goldwell::Colorance::US"

TOPCHIC_MIX_SHADES = ["A-Mix", "P-Mix", "VV", "RR", "KK", "GG"]
COLORANCE_SPECIAL_SHADES = ["CLEAR", "GG", "KK", "RR", "VV", "P-Mix"]

# Longest-token-first Goldwell suffix legend (Color Continuum + product book headers).
GOLDWELL_TOKENS: dict[str, tuple[str, list[str], str]] = {
    "NA": ("confirmed", "Natural Ash", ["Natural", "Ash"], "N/NA column family"),
    "NN": ("confirmed", "Natural Natural", ["Natural", "Neutral"], "NN extra-coverage naturals"),
    "GB": ("confirmed", "Gold Beige", ["Gold", "Beige"], "printed GB column"),
    "GN": ("inferred", "Gold Natural", ["Gold", "Natural"], "GN column header"),
    "BB": ("inferred", "Beige Brown", ["Beige", "Brown"], "BB column header"),
    "BG": ("inferred", "Brown Gold", ["Brown", "Gold"], "BG column header"),
    "KN": ("inferred", "Copper Natural", ["Copper", "Natural"], "KN column header"),
    "BN": ("inferred", "Brown Natural", ["Brown", "Natural"], "BN column header"),
    "KS": ("inferred", "Copper Sand", ["Copper", "Beige"], "KS column header"),
    "RB": ("confirmed", "Red Brown", ["Red", "Brown"], "RB column header"),
    "KG": ("inferred", "Copper Gold", ["Copper", "Gold"], "KG column header"),
    "KR": ("inferred", "Copper Red", ["Copper", "Red"], "KR column header"),
    "OR": ("confirmed", "Orange", ["Copper", "Red"], "OR Max family"),
    "OO": ("inferred", "Orange", ["Copper", "Warm"], "OO Max family"),
    "RO": ("confirmed", "Red Orange", ["Red", "Copper"], "RO Max family"),
    "SB": ("inferred", "Sand Beige", ["Beige", "Warm"], "SB column header"),
    "VA": ("inferred", "Violet Ash", ["Violet", "Ash"], "VA column header"),
    "BP": ("inferred", "Beige Pearl", ["Beige", "Pearl"], "BP column header"),
    "BA": ("confirmed", "Beige Ash", ["Beige", "Ash"], "BA column header"),
    "BM": ("inferred", "Brown Mahogany", ["Brown", "Mahogany"], "BM column header"),
    "MB": ("inferred", "Mocha Brown", ["Mocha", "Brown"], "MB column header"),
    "BS": ("inferred", "Brown Sand", ["Brown", "Beige"], "BS column header"),
    "CA": ("inferred", "Cover Plus Ash", ["Ash", "Cool"], "8CA Colorance Cover Plus family"),
    "BV": ("inferred", "Blue Violet", ["Blue", "Violet"], "BV column header"),
    "VV": ("confirmed", "Violet Violet", ["Violet"], "Mix shade VV"),
    "RR": ("confirmed", "Red Red", ["Red"], "Mix shade RR"),
    "KK": ("inferred", "Copper Copper", ["Copper"], "Mix shade KK"),
    "GG": ("confirmed", "Gold Gold", ["Gold"], "Mix shade GG"),
    "SV": ("inferred", "Silver Violet", ["Pearl", "Violet"], "11SV HiBlondes family"),
    "RS": ("inferred", "Red Sand", ["Red", "Beige"], "5RS family"),
    "RV": ("inferred", "Red Violet", ["Red", "Violet"], "6RV family"),
    "PK": ("inferred", "Pearl Copper", ["Pearl", "Copper"], "7PK family"),
    "N": ("confirmed", "Natural", ["Natural"], "N naturals"),
    "G": ("confirmed", "Gold", ["Gold"], "G golds"),
    "B": ("confirmed", "Brown", ["Brown"], "B browns"),
    "K": ("confirmed", "Copper", ["Copper"], "K coppers"),
    "A": ("confirmed", "Ash", ["Ash"], "A ashes"),
    "R": ("confirmed", "Red", ["Red"], "R reds"),
    "V": ("confirmed", "Violet", ["Violet"], "V violets"),
    "P": ("confirmed", "Pearl", ["Pearl"], "P pearls"),
    "M": ("inferred", "Mocha", ["Mocha"], "M mochas"),
}

GOLDWELL_SPECIAL = {
    "CLEAR": ("confirmed", "Clear", [], "Colorance Clear diluter"),
    "A-Mix": ("confirmed", "Ash Mix", ["Ash", "Cool"], "Topchic cool mix additive"),
    "P-Mix": ("confirmed", "Pearl Mix", ["Pearl", "Cool"], "Cool mix additive"),
}


def _tokenize_tone(body: str) -> list[str]:
    if body in GOLDWELL_SPECIAL:
        return [body]
    tokens: list[str] = []
    i = 0
    while i < len(body):
        matched = None
        for length in range(min(4, len(body) - i), 0, -1):
            piece = body[i : i + length]
            if piece in GOLDWELL_TOKENS or piece in GOLDWELL_SPECIAL:
                matched = piece
                break
        if matched is None:
            return [body]
        tokens.append(matched)
        i += len(matched)
    return tokens


def parse_shade_code(shade_code: str) -> tuple[int | None, list[str]]:
    if shade_code in GOLDWELL_SPECIAL:
        return None, [shade_code]
    match = re.match(r"^(\d{1,2})([A-Za-z-]+)$", shade_code)
    if not match:
        return None, [shade_code]
    return int(match.group(1)), _tokenize_tone(match.group(2).upper())


def decode_token(token: str) -> tuple[str, str, list[str], str] | None:
    if token in GOLDWELL_SPECIAL:
        st, term, tones, why = GOLDWELL_SPECIAL[token]
        return st, term, tones, why
    if token not in GOLDWELL_TOKENS:
        return None
    st, term, tones, why = GOLDWELL_TOKENS[token]
    return st, term, tones, why


def extract_topchic_from_product_book(text: str) -> list[str]:
    codes: set[str] = set()
    for code in re.findall(r"\b\d{1,2}[A-Z]{1,4}\b", text):
        if re.match(r"^\d{1,2}[A-Z]{1,4}$", code):
            codes.add(code)
    for code in re.findall(r"\b\d{1,2}(?:N|NA|NN)\b", text):
        codes.add(code)
    codes.update(TOPCHIC_MIX_SHADES)
    return sorted(codes, key=lambda x: (int(re.match(r"\d+", x).group()) if re.match(r"^\d", x) else 99, x))


def extract_colorance_from_continuum(text: str) -> list[str]:
    codes: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not re.match(r"^\d{1,2}\s", line):
            continue
        for part in re.split(r"\s+", line)[1:]:
            if part in {"Max", "TC", "COL", "RO"}:
                continue
            if part == "80R":
                codes.add("8OR")
                continue
            if part == "700":
                codes.add("7OO")
                continue
            if re.match(r"^\d{1,2}N/NN$", part):
                lvl = part[: part.index("N")]
                codes.add(f"{lvl}N")
                codes.add(f"{lvl}NN")
                continue
            if re.match(r"^\d{1,2}(?:N|NA|NN)$", part) or re.match(r"^\d{1,2}[A-Z]{1,4}$", part):
                codes.add(part)
    for code in ("7RO", "7NA", "7A", "7MB", "7SB"):
        codes.add(code)
    codes.update(COLORANCE_SPECIAL_SHADES)
    return sorted(codes, key=lambda x: (int(re.match(r"\d+", x).group()) if re.match(r"^\d", x) else 99, x))


def load_pdf_texts() -> tuple[str, str]:
    try:
        import pypdf
    except ImportError as exc:
        raise SystemExit("pypdf required: pip install pypdf") from exc

    book_path = os.path.join(OUT, "sources", "goldwell_product_book_2018.pdf")
    continuum_path = os.path.join(OUT, "sources", "goldwell_color_continuum_2020.pdf")
    os.makedirs(os.path.dirname(book_path), exist_ok=True)

    if not os.path.exists(book_path):
        import urllib.request

        urllib.request.urlretrieve(PRODUCT_BOOK_URL, book_path)
    if not os.path.exists(continuum_path):
        import urllib.request

        urllib.request.urlretrieve(CONTINUUM_URL, continuum_path)

    book = pypdf.PdfReader(book_path)
    continuum = pypdf.PdfReader(continuum_path)
    return book.pages[8].extract_text() or "", continuum.pages[68].extract_text() or ""


def line_technical_records() -> list[dict[str, Any]]:
    return [
        {
            "canonical_key": TOPCHIC_KEY,
            "brand": "Goldwell",
            "product_line": "Topchic",
            "color_type": "permanent",
            "default_mixing_ratio": "1:1 color:TOPCHIC Cream Developer Lotion",
            "developer_options": [
                "TOPCHIC Cream Developer Lotion 3% (10 vol.)",
                "6% (20 vol.)",
                "9% (30 vol.)",
                "12% (40 vol.)",
            ],
            "developer_strengths_if_stated": "Virgin-hair deposit/lift table on Color Guide",
            "processing_time_ranges": None,
            "gray_coverage_rules": "N-/NA-/NN- vs Fashion shade mixing by % white (printed table)",
            "lift_rules": "Up to 3 levels virgin hair with 12% (40 vol.); 11/12 HiBlondes series up to 4-5 levels",
            "tone_family_legend": [],
            "special_usage_notes": [
                "Equalizer System 2.0 + Integrated Protect System (IPS) per product book.",
                "Mix shades A-Mix, P-Mix, VV, RR, KK, GG are intermix additives (Color Continuum ch.7).",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per Goldwell product book / Color Continuum",
            "source_url": COLOR_GUIDE_TOPCHIC_URL,
            "source_document": "Goldwell Product Book 2018 (Topchic shade grid p.17) + US Color Guide",
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": ["Shade names not printed per code in extracted PDF grids."],
        },
        {
            "canonical_key": COLORANCE_KEY,
            "brand": "Goldwell",
            "product_line": "Colorance (incl. Cover Plus, Gloss Tones)",
            "color_type": "demi-permanent",
            "default_mixing_ratio": "2:1 Colorance Lotion : color (standard); Cover Plus 2:1 Cover Plus Lotion",
            "developer_options": ["Colorance Lotion", "Colorance Cover Plus Lotion", "Colorance Express Toning Lotion"],
            "developer_strengths_if_stated": "Colorance Lotion only (demi deposit)",
            "processing_time_ranges": ["Up to 25 minutes standard; Express Toning 5 minutes"],
            "gray_coverage_rules": "Fashion + N-shade mixing up to 50%; Cover Plus NN up to 75%",
            "lift_rules": "Deposit only",
            "tone_family_legend": [],
            "special_usage_notes": [
                "IntraLipid Technology; ammonia-free demi-permanent.",
                "Mix shades GG, KK, RR, VV, P-Mix; Clear dilutes deposit.",
            ],
            "region_or_market": "US",
            "discontinued_status": "Active per Goldwell Color Continuum",
            "source_url": COLOR_GUIDE_COLORANCE_URL,
            "source_document": "Goldwell Color Continuum 2020 (Colorance ch.10 + shared shade matrix p.69)",
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": [
                "Express Toning and Gloss Tones named shades not in shared numeric matrix; numeric core palette extracted.",
            ],
        },
    ]


def build_line_records(
    *,
    canonical_key: str,
    product_line: str,
    shade_codes: list[str],
    color_type: str,
    source_url: str,
    source_document: str,
    line_tech: dict[str, Any],
    collection_notes: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw_records: list[dict[str, Any]] = []
    tone_map: dict[tuple[str, str], dict[str, Any]] = {}
    tone_reference: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    for shade_code in shade_codes:
        level, tone_codes = parse_shade_code(shade_code)
        raw = {
            "canonical_key": canonical_key,
            "brand": "Goldwell",
            "product_line": product_line,
            "shade_code": shade_code,
            "shade_name": None,
            "level": level,
            "manufacturer_tone_codes": tone_codes,
            "manufacturer_tone_descriptions": [],
            "color_type": color_type,
            "gray_coverage_claim": None,
            "lift_capability": line_tech.get("lift_rules", [None])[0] if line_tech.get("lift_rules") else None,
            "mixing_ratio": line_tech.get("default_mixing_ratio"),
            "developer_recommendations": line_tech.get("developer_options", []),
            "processing_time_minutes": None,
            "special_usage_notes": collection_notes,
            "official_swatch_image_exists": None,
            "region_or_market": "US",
            "source_url": source_url,
            "source_document": source_document,
            "source_type": "official_pdf_catalog",
            "source_publication_date": "2018" if "2018" in source_document else "2020",
            "source_confidence": "high",
            "evidence_status": "confirmed",
            "assumptions": [],
            "data_gaps": ["Shade name not printed per code in source PDF grid."],
        }
        raw_records.append(raw)

        for code in tone_codes:
            key = (canonical_key, code)
            if key in tone_map:
                continue
            decoded = decode_token(code)
            if decoded is None:
                tone_reference.append(
                    {
                        "canonical_key": canonical_key,
                        "brand": "Goldwell",
                        "product_line": product_line,
                        "manufacturer_tone_code": code,
                        "manufacturer_term": None,
                        "manufacturer_definition": None,
                        "confidence": "unresolved",
                        "notes_on_ambiguity": [f"Could not decode Goldwell token {code!r}"],
                    }
                )
                continue
            status, term, tones, why = decoded
            tone_reference.append(
                {
                    "canonical_key": canonical_key,
                    "brand": "Goldwell",
                    "product_line": product_line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": term,
                    "manufacturer_definition": why,
                    "confidence": "high" if status == "confirmed" else "medium",
                    "notes_on_ambiguity": [] if status == "confirmed" else [why],
                }
            )
            tone_map[key] = {
                "canonical_key": canonical_key,
                "brand": "Goldwell",
                "product_line": product_line,
                "manufacturer_tone_code": code,
                "manufacturer_term": term,
                "normalized_tones": tones,
                "mapping_rationale": why,
                "mapping_confidence": "high" if status == "confirmed" else "medium",
                "ambiguity_flag": status != "confirmed",
                "notes": [],
            }

        tones: list[str] = []
        gaps = list(raw.get("data_gaps") or [])
        for code in tone_codes:
            mapping = tone_map.get((canonical_key, code))
            if mapping:
                for tone in mapping["normalized_tones"]:
                    if tone not in tones:
                        tones.append(tone)
            else:
                gaps.append(f"Tone code {code} unresolved")
        normalized.append(
            {
                "canonical_key": canonical_key,
                "brand": "Goldwell",
                "product_line": product_line,
                "shade_code": shade_code,
                "shade_name": None,
                "level": level,
                "manufacturer_tone_codes": tone_codes,
                "manufacturer_tone_descriptions": [],
                "normalized_tones": tones,
                "color_type": color_type,
                "gray_coverage_claim": None,
                "lift_levels": raw.get("lift_capability"),
                "mixing_ratio": line_tech.get("default_mixing_ratio"),
                "developer_options": line_tech.get("developer_options"),
                "processing_time_minutes": None,
                "special_usage_notes": collection_notes,
                "official_swatch_image_exists": None,
                "region_or_market": "US",
                "discontinued_status": line_tech.get("discontinued_status"),
                "source_url": source_url,
                "source_document": source_document,
                "source_type": "official_pdf_catalog",
                "source_publication_date": raw.get("source_publication_date"),
                "source_confidence": "high",
                "evidence_status": "confirmed",
                "assumptions": ["mixing_ratio inherited from line-level record (batch07)"],
                "data_gaps": gaps,
            }
        )

    return raw_records, list(tone_map.values()), tone_reference, normalized


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    book_text, continuum_text = load_pdf_texts()
    topchic_codes = extract_topchic_from_product_book(book_text)
    colorance_codes = extract_colorance_from_continuum(continuum_text)

    tech_by_key = {row["canonical_key"]: row for row in line_technical_records()}
    top_raw, top_map, top_ref, top_norm = build_line_records(
        canonical_key=TOPCHIC_KEY,
        product_line="Topchic",
        shade_codes=topchic_codes,
        color_type="permanent",
        source_url=PRODUCT_BOOK_URL,
        source_document="Goldwell Product Book 2018 (Topchic shade grid p.17)",
        line_tech=tech_by_key[TOPCHIC_KEY],
        collection_notes="Topchic permanent palette grid transcribed from product book PDF.",
    )
    col_raw, col_map, col_ref, col_norm = build_line_records(
        canonical_key=COLORANCE_KEY,
        product_line="Colorance (incl. Cover Plus, Gloss Tones)",
        shade_codes=colorance_codes,
        color_type="demi-permanent",
        source_url=CONTINUUM_URL,
        source_document="Goldwell Color Continuum 2020 (shared Topchic/Colorance matrix p.69)",
        line_tech=tech_by_key[COLORANCE_KEY],
        collection_notes="Colorance demi palette from Color Continuum matrix + mix/clear specials.",
    )

    raw_records = top_raw + col_raw
    tone_map = top_map + col_map
    tone_reference = top_ref + col_ref
    normalized = top_norm + col_norm

    def save(name: str, payload: dict[str, Any]) -> None:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    save(
        "goldwell_batch07_raw_shade_records.json",
        {"artifact": "raw_shade_records", "batch": "goldwell_batch07", "count": len(raw_records), "raw_shade_records": raw_records},
    )
    save(
        "goldwell_batch07_line_technical_records.json",
        {"artifact": "line_technical_records", "batch": "goldwell_batch07", "count": 2, "line_technical_records": list(tech_by_key.values())},
    )
    save(
        "goldwell_batch07_tone_normalization_map.json",
        {"artifact": "tone_normalization_map", "batch": "goldwell_batch07", "count": len(tone_map), "tone_normalization_map": tone_map},
    )
    save(
        "goldwell_batch07_manufacturer_tone_reference.json",
        {
            "artifact": "manufacturer_tone_reference",
            "batch": "goldwell_batch07",
            "count": len(tone_reference),
            "manufacturer_tone_reference": tone_reference,
        },
    )
    save(
        "normalized_shade_records_batch_7.json",
        {"artifact": "normalized_shade_records", "batch": 7, "count": len(normalized), "normalized_shade_records": normalized},
    )
    save(
        "batch_7_manifest.json",
        {
            "batch": 7,
            "label": "goldwell_topchic_colorance",
            "lines_added": [TOPCHIC_KEY, COLORANCE_KEY],
            "shade_count": len(normalized),
            "sources": [PRODUCT_BOOK_URL, CONTINUUM_URL, COLOR_GUIDE_TOPCHIC_URL, COLOR_GUIDE_COLORANCE_URL],
        },
    )

    print(f"Goldwell batch07 built: {len(normalized)} normalized shades")
    print(f"  Topchic: {len(top_norm)}")
    print(f"  Colorance: {len(col_norm)}")
    print(f"  Tone mappings: {len(tone_map)}")


if __name__ == "__main__":
    main()
