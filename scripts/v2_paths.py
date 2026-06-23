"""Filesystem paths for ColorSynth Formula Engine v2."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE12_DIR = REPO_ROOT / "hair_color_db" / "stage12_package"
STAGE13_DIR = REPO_ROOT / "hair_color_db" / "stage13_formulation_rules"

SHADES_JSON = STAGE12_DIR / "C_normalized_shade_records.json"
LINE_INVENTORY_JSON = STAGE12_DIR / "A_brand_line_inventory.json"
LINE_TECH_JSON = STAGE12_DIR / "D_line_technical_records.json"
CROSS_LINE_JSON = STAGE12_DIR / "J_cross_line_conversion_map.json"

UNIVERSAL_RULES_JSON = STAGE13_DIR / "B_universal_rule_library.json"
LINE_OVERRIDES_JSON = STAGE13_DIR / "D_brand_line_overrides.json"
FORMULATION_ONTOLOGY_JSON = STAGE13_DIR / "A_formulation_ontology.json"

SEED_DIR = REPO_ROOT / "data" / "seed"
SHADES_CSV = SEED_DIR / "shades.csv"
FORMULATION_RULES_CSV = SEED_DIR / "formulation_rules.csv"
CROSS_LINE_MAPPINGS_CSV = SEED_DIR / "cross_line_mappings.csv"
BRANDS_LINES_CSV = SEED_DIR / "brands_lines.csv"

# Authoritative inventory (repo-verified 2026-06-22)
EXPECTED_SHADE_COUNT = 2537
EXPECTED_CROSS_LINE_COUNT = 1032
