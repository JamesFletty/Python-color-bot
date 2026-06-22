"""Filesystem paths for hair color database artifacts."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HAIR_COLOR_DB = REPO_ROOT / "hair_color_db"
STAGE12 = HAIR_COLOR_DB / "stage12_package"
SCHEMA_PROPOSAL = HAIR_COLOR_DB / "stage10_schema" / "schema_proposal.json"

SHADES_JSON = STAGE12 / "C_normalized_shade_records.json"
TONE_MAP_JSON = STAGE12 / "F_tone_normalization_map.json"
LINE_TECH_JSON = STAGE12 / "D_line_technical_records.json"

CROSS_LINE_JSON = STAGE12 / "J_cross_line_conversion_map.json"

DEFAULT_DB_PATH = REPO_ROOT / "hair_color.db"
VERIFICATION_REPORT_PATH = REPO_ROOT / "hair_color_db_verification_report.json"

EXPECTED_SHADE_COUNT = 2456
EXPECTED_TONE_MAPPING_COUNT = 950
