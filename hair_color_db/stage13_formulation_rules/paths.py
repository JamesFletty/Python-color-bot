"""Paths for Stage 13 formulation rules package."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
STAGE12_DIR = PACKAGE_DIR.parent / "stage12_package"

ARTIFACT_FILES = {
    "A": PACKAGE_DIR / "A_formulation_ontology.json",
    "B": PACKAGE_DIR / "B_universal_rule_library.json",
    "C": PACKAGE_DIR / "C_service_workflows.json",
    "D": PACKAGE_DIR / "D_brand_line_overrides.json",
    "E": PACKAGE_DIR / "E_decision_order.json",
    "F": PACKAGE_DIR / "F_validation_cases.json",
    "G": PACKAGE_DIR / "G_conflicts_and_gaps.json",
    "H": PACKAGE_DIR / "H_schema_extension_proposal.json",
    "I": PACKAGE_DIR / "I_integration_notes.md",
    "MANIFEST": PACKAGE_DIR / "MANIFEST.json",
}

SHADES_JSON = STAGE12_DIR / "C_normalized_shade_records.json"
LINE_INVENTORY_JSON = STAGE12_DIR / "A_brand_line_inventory.json"
