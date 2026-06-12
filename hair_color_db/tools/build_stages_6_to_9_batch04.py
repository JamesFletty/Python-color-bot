#!/usr/bin/env python3
"""Build Batch 4 Stage 6-9 artifacts."""
import glob
import json
import os
import re
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), "..")
B4 = os.path.join(BASE, "batches", "batch04")
TAXONOMY = {
    "Natural",
    "Neutral",
    "Ash",
    "Blue",
    "Green",
    "Violet",
    "Pearl",
    "Gold",
    "Beige",
    "Copper",
    "Red",
    "Mahogany",
    "Mocha",
    "Brown",
    "Warm",
    "Cool",
    "Other",
}

raw, line_tech = [], []
for f in sorted(glob.glob(os.path.join(B4, "*_raw_shade_records.json"))):
    raw += json.load(open(f, encoding="utf-8")).get("raw_shade_records", [])
if not raw:
    data = json.load(open(os.path.join(B4, "raw_shade_records_batch_4.json"), encoding="utf-8"))
    raw = data["raw_shade_records"]

for f in sorted(glob.glob(os.path.join(B4, "*_line_technical_records.json"))):
    line_tech += json.load(open(f, encoding="utf-8"))["line_technical_records"]
tech_by_key = {t["canonical_key"]: t for t in line_tech}


def kenra_tone_map(suffix):
    mapping = {
        "N": (["Natural", "Neutral"], "N = Natural/Neutral"),
        "NA": (["Neutral", "Ash"], "NA = Neutral Ash"),
        "NB": (["Neutral", "Beige"], "NB = Neutral Brown/Beige"),
        "NUA": (["Neutral", "Ash"], "NUA = Neutral Ultra Ash"),
        "UA": (["Ash"], "UA = Ultra Ash"),
        "A": (["Ash"], "A = Ash"),
        "AA": (["Ash"], "AA = double Ash"),
        "G": (["Gold"], "G = Gold"),
        "GB": (["Gold", "Beige"], "GB = Gold Beige"),
        "B": (["Brown", "Beige"], "B = Brown/Beige"),
        "BC": (["Brown", "Copper"], "BC = Brown/Copper"),
        "C": (["Copper"], "C = Copper"),
        "R": (["Red"], "R = Red"),
        "RR": (["Red"], "RR = double Red"),
        "RC": (["Red", "Copper"], "RC = Red Copper"),
        "RB": (["Red", "Brown"], "RB = Red Brown"),
        "RV": (["Red", "Violet"], "RV = Red Violet"),
        "VR": (["Violet", "Red"], "VR = Violet Red"),
        "V": (["Violet"], "V = Violet"),
        "VV": (["Violet"], "VV = double Violet"),
        "VM": (["Violet", "Mocha"], "VM = Violet Mocha"),
        "PV": (["Pearl", "Violet"], "PV = Pearl Violet"),
        "SM": (["Mocha"], "SM = Smokey Mocha"),
        "CN": (["Copper", "Neutral"], "CN = Copper Neutral"),
        "Bl": (["Blue"], "1Bl = Blue black"),
        "DF": (["Pearl", "Cool"], "DF = Diamond Frost demi booster"),
        "B": (["Blue"], "Rapid Toner B = Blue"),
        "SA": (["Ash", "Neutral"], "Rapid Toner Smokey Ash"),
        "SV": (["Violet", "Other"], "Rapid Toner Silver Violet"),
        "VP": (["Violet", "Pearl"], "Rapid Toner Violet Pearl"),
        "GrBl": (["Blue", "Ash"], "Rapid Toner Gray Blue"),
        "GV": (["Gold", "Violet"], "Rapid Toner Gold Violet"),
        "RoV": (["Red", "Violet"], "Rapid Toner Rose Violet"),
    }
    if suffix in mapping:
        tones, why = mapping[suffix]
        flag = suffix in ("NUA", "UA", "VM", "SM", "CN", "SV", "GrBl")
        return tones, suffix, why, flag
    return ["Other"], suffix, f"Kenra suffix {suffix!r} not in legend", True


def vivids_tone(name):
    c = name.lower()
    for k, tones in [
        ("blue", ["Blue"]),
        ("pink", ["Red"]),
        ("magenta", ["Red", "Violet"]),
        ("red", ["Red"]),
        ("violet", ["Violet"]),
        ("berry", ["Red", "Violet"]),
    ]:
        if k in c:
            return tones, k in ("berry",), f"shade name contains {k!r}"
    return ["Other"], True, "Everlasting named shade"


def pulpriot_tone(name):
    c = name.lower()
    rules = [
        ("clear", []),
        ("aquatic", ["Blue", "Green"]),
        ("absinthe", ["Green"]),
        ("blush", ["Red"]),
        ("fireball", ["Copper", "Red"]),
        ("lemon", ["Gold"]),
        ("lilac", ["Violet"]),
        ("nightfall", ["Violet", "Blue"]),
        ("jam", ["Red", "Mahogany"]),
        ("cupid", ["Red"]),
        ("silver", ["Other", "Cool"]),
        ("violet", ["Violet"]),
        ("pink", ["Red"]),
        ("orange", ["Copper"]),
        ("blue", ["Blue"]),
        ("green", ["Green"]),
        ("red", ["Red"]),
        ("yellow", ["Gold"]),
        ("purple", ["Violet"]),
        ("teal", ["Blue", "Green"]),
    ]
    for k, tones in rules:
        if k in c:
            return tones, k == "silver", f"Pulp Riot shade name contains {k!r}"
    return ["Other"], False, "Pulp Riot direct-dye shade name"


observed = defaultdict(set)
for r in raw:
    key = r["canonical_key"]
    if r["manufacturer_tone_codes"]:
        for c in r["manufacturer_tone_codes"]:
            observed[key].add(c)
    else:
        observed[key].add(r["shade_code"])

tone_reference, norm_map, unresolved, ambiguous_codes = [], [], [], []

for key in sorted(observed):
    brand, line = key.split("::")[0], key.split("::")[1]
    tech = tech_by_key.get(key, {})
    src_url, src_doc = tech.get("source_url", ""), tech.get("source_document", "")

    for code in sorted(observed[key]):
        if key.startswith("Kenra Professional::"):
            if key.endswith("Rapid Toners::US"):
                tones, term, why, flag = kenra_tone_map(code)
            elif key.endswith("Studio Stylist Express::US"):
                sse = {
                    "N": (["Natural", "Neutral"], "SSE N series"),
                    "NB": (["Neutral", "Beige"], "SSE NB series"),
                    "A": (["Ash"], "SSE A series"),
                    "B": (["Brown", "Beige"], "SSE B series"),
                    "G": (["Gold"], "SSE G series"),
                }
                suffix = re.sub(r"^\d{1,2}", "", code)
                letter = suffix[:1] if suffix in ("N", "A", "G") else suffix[:2]
                if letter in sse:
                    tones, why = sse[letter]
                    term, flag = letter, False
                else:
                    tones, term, why, flag = kenra_tone_map(suffix)
            else:
                suffix = code if code in ("DF", "Bl") else re.sub(r"^\d{1,2}", "", code)
                tones, term, why, flag = kenra_tone_map(suffix)
            conf = "medium" if flag else "high"
            tone_reference.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": term,
                    "manufacturer_definition": why,
                    "evidence_source_url": src_url,
                    "evidence_source_document": src_doc,
                    "confidence": conf,
                    "notes_on_ambiguity": ([] if not flag else [why]),
                }
            )
            if flag:
                ambiguous_codes.append(
                    {
                        "canonical_key": key,
                        "manufacturer_tone_code": code,
                        "ambiguity_reason": "partial_legend",
                        "details": why,
                    }
                )
            norm_map.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": term,
                    "normalized_tones": tones,
                    "mapping_rationale": why,
                    "mapping_confidence": conf,
                    "ambiguity_flag": flag,
                    "notes": [],
                }
            )
        elif key == "Pravana::ChromaSilk VIVIDS Everlasting::US":
            tones, flag, why = vivids_tone(code)
            tone_reference.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "manufacturer_definition": why,
                    "evidence_source_url": src_url,
                    "evidence_source_document": src_doc,
                    "confidence": "medium" if flag else "high",
                    "notes_on_ambiguity": ([] if not flag else [why]),
                }
            )
            norm_map.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "normalized_tones": tones,
                    "mapping_rationale": why,
                    "mapping_confidence": "medium" if flag else "high",
                    "ambiguity_flag": flag,
                    "notes": [],
                }
            )
        elif key == "Pulp Riot::Semi-Permanent::US":
            tones, flag, why = pulpriot_tone(code)
            tone_reference.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "manufacturer_definition": why,
                    "evidence_source_url": src_url,
                    "evidence_source_document": src_doc,
                    "confidence": "high" if not flag else "medium",
                    "notes_on_ambiguity": ([] if not flag else [why]),
                }
            )
            norm_map.append(
                {
                    "canonical_key": key,
                    "brand": brand,
                    "product_line": line,
                    "manufacturer_tone_code": code,
                    "manufacturer_term": code,
                    "normalized_tones": tones,
                    "mapping_rationale": why,
                    "mapping_confidence": "high" if not flag else "medium",
                    "ambiguity_flag": flag,
                    "notes": [],
                }
            )

assert all(set(m["normalized_tones"]) <= TAXONOMY for m in norm_map)

json.dump(
    {
        "stage": 6,
        "artifact": "manufacturer_tone_reference",
        "batch": 4,
        "completion_status": "complete",
        "manufacturer_tone_reference": tone_reference,
        "ambiguous_tone_codes": ambiguous_codes,
        "issue_log": [
            {
                "item": "Kenra multi-letter suffixes",
                "issue_type": "legend_gap",
                "details": "Some Kenra wall-chart suffixes (NUA, VM, CN) lack explicit definitions in workbook text layer.",
            }
        ],
    },
    open(os.path.join(B4, "manufacturer_tone_reference_batch_4.json"), "w"),
    indent=2,
    ensure_ascii=False,
)

json.dump(
    {
        "stage": 7,
        "artifact": "tone_normalization_map",
        "batch": 4,
        "completion_status": "complete",
        "tone_normalization_map": norm_map,
        "unresolved_mappings": unresolved,
        "issue_log": [],
    },
    open(os.path.join(B4, "tone_normalization_map_batch_4.json"), "w"),
    indent=2,
    ensure_ascii=False,
)

map_idx = {(m["canonical_key"], m["manufacturer_tone_code"]): m for m in norm_map}
normalized, merge_issues = [], []
for r in raw:
    key = r["canonical_key"]
    tech = tech_by_key.get(key, {})
    tones, gaps, assumptions = [], list(r.get("data_gaps") or []), list(r.get("assumptions") or [])
    codes = r["manufacturer_tone_codes"] or [r["shade_code"]]
    for c in codes:
        m = map_idx.get((key, c))
        if m:
            for t in m["normalized_tones"]:
                if t not in tones:
                    tones.append(t)
        elif c.lower() != "clear":
            gaps.append(f"tone code {c} unresolved; no normalized tones assigned")
    mixing = r.get("mixing_ratio")
    if mixing is None and tech.get("default_mixing_ratio"):
        mixing = tech["default_mixing_ratio"]
        assumptions.append("mixing_ratio inherited from line-level default (Stage 5 record)")
    devs = r.get("developer_recommendations") or []
    if not devs and tech.get("developer_options"):
        devs = tech["developer_options"]
        assumptions.append("developer_options inherited from line-level record (Stage 5)")
    normalized.append(
        {
            "canonical_key": key,
            "brand": r["brand"],
            "product_line": r["product_line"],
            "shade_code": r["shade_code"],
            "shade_name": r["shade_name"],
            "level": r["level"],
            "manufacturer_tone_codes": r["manufacturer_tone_codes"] or codes,
            "manufacturer_tone_descriptions": r["manufacturer_tone_descriptions"],
            "normalized_tones": tones,
            "color_type": r.get("color_type") or tech.get("color_type"),
            "gray_coverage_claim": r.get("gray_coverage_claim"),
            "lift_levels": r.get("lift_capability"),
            "mixing_ratio": mixing,
            "developer_options": devs,
            "processing_time_minutes": r.get("processing_time_minutes"),
            "special_usage_notes": r.get("special_usage_notes"),
            "official_swatch_image_exists": r.get("official_swatch_image_exists"),
            "region_or_market": r.get("region_or_market"),
            "discontinued_status": tech.get("discontinued_status"),
            "source_url": r["source_url"],
            "source_document": r["source_document"],
            "source_type": r["source_type"],
            "source_publication_date": r.get("source_publication_date"),
            "source_confidence": r["source_confidence"],
            "evidence_status": r["evidence_status"],
            "assumptions": assumptions,
            "data_gaps": gaps,
        }
    )

json.dump(
    {
        "stage": 8,
        "artifact": "normalized_shade_records",
        "batch": 4,
        "completion_status": "complete",
        "normalized_shade_records": normalized,
        "merge_issues": merge_issues,
        "issue_log": [],
    },
    open(os.path.join(B4, "normalized_shade_records_batch_4.json"), "w"),
    indent=2,
    ensure_ascii=False,
)

findings = []
seen = defaultdict(list)
for n in normalized:
    seen[(n["canonical_key"], n["shade_code"])].append(n)
for (key, code), rows in seen.items():
    if len(rows) > 1:
        findings.append(
            {
                "canonical_key": key,
                "record_ref": code,
                "issue_type": "duplicate_shade_code",
                "severity": "high",
                "details": f"{len(rows)} normalized records share shade_code {code}",
                "recommended_fix": "Distinguish sub-range variants or deduplicate.",
            }
        )
for n in normalized:
    ref = f"{n['canonical_key']}#{n['shade_code']}"
    if not n["source_url"]:
        findings.append(
            {
                "canonical_key": n["canonical_key"],
                "record_ref": ref,
                "issue_type": "missing_provenance",
                "severity": "high",
                "details": "source_url empty",
                "recommended_fix": "Re-extract with source captured.",
            }
        )
    if (
        n["manufacturer_tone_codes"]
        and not n["normalized_tones"]
        and "clear" not in str(n["shade_code"]).lower()
    ):
        findings.append(
            {
                "canonical_key": n["canonical_key"],
                "record_ref": ref,
                "issue_type": "unmapped_tone_codes",
                "severity": "medium",
                "details": "manufacturer_tone_codes present but normalized_tones empty",
                "recommended_fix": "Add tone mapping or mark as diluter.",
            }
        )

kenra_pdf = [n for n in normalized if "Kenra" in n["canonical_key"]]
if kenra_pdf and all(n["shade_name"] == n["shade_code"] for n in kenra_pdf[:5]):
    findings.append(
        {
            "canonical_key": "Kenra Professional::Kenra Color Permanent::US",
            "record_ref": "wall_chart_batch",
            "issue_type": "shade_name_defaulted_to_code",
            "severity": "low",
            "details": "Kenra wall chart PDF text layer lists codes without companion shade display names.",
            "recommended_fix": "Augment from swatchbook or product pages when available.",
        }
    )

json.dump(
    {
        "stage": 9,
        "artifact": "qa_findings",
        "batch": 4,
        "completion_status": "complete",
        "qa_findings": findings,
        "summary": {
            "records_reviewed": len(normalized),
            "findings_count": len(findings),
            "high_severity": sum(1 for f in findings if f["severity"] == "high"),
        },
    },
    open(os.path.join(B4, "qa_findings_batch_4.json"), "w"),
    indent=2,
    ensure_ascii=False,
)

print("tone_reference", len(tone_reference))
print("norm_map", len(norm_map))
print("normalized", len(normalized))
print("qa_findings", len(findings))
