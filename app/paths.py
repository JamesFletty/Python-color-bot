"""Filesystem paths for v2 runtime."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE13_DIR = REPO_ROOT / "hair_color_db" / "stage13_formulation_rules"
FORMULATION_ONTOLOGY_JSON = STAGE13_DIR / "A_formulation_ontology.json"
