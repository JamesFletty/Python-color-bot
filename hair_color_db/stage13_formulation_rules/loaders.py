"""Load Stage 13 package artifacts and Stage 12 inventory indexes."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .paths import ARTIFACT_FILES, LINE_INVENTORY_JSON, SHADES_JSON


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON artifact."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_ontology() -> dict[str, Any]:
    return load_json(ARTIFACT_FILES["A"])


@lru_cache(maxsize=1)
def load_universal_rules() -> list[dict[str, Any]]:
    return load_json(ARTIFACT_FILES["B"])["universal_rules"]


@lru_cache(maxsize=1)
def load_service_workflows() -> list[dict[str, Any]]:
    return load_json(ARTIFACT_FILES["C"])["service_workflows"]


@lru_cache(maxsize=1)
def load_line_overrides() -> list[dict[str, Any]]:
    return load_json(ARTIFACT_FILES["D"])["brand_line_overrides"]


@lru_cache(maxsize=1)
def load_decision_order() -> dict[str, Any]:
    return load_json(ARTIFACT_FILES["E"])


@lru_cache(maxsize=1)
def load_validation_cases() -> list[dict[str, Any]]:
    return load_json(ARTIFACT_FILES["F"])["validation_cases"]


@lru_cache(maxsize=1)
def load_conflicts_and_gaps() -> list[dict[str, Any]]:
    return load_json(ARTIFACT_FILES["G"])["conflicts_and_gaps"]


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    return load_json(ARTIFACT_FILES["MANIFEST"])


@lru_cache(maxsize=1)
def stage12_canonical_keys_with_shades() -> set[str]:
    """Canonical keys that have at least one normalized shade in Stage 12."""
    payload = load_json(SHADES_JSON)
    return {
        str(record["canonical_key"])
        for record in payload.get("normalized_shade_records", [])
        if record.get("canonical_key")
    }


@lru_cache(maxsize=1)
def stage12_inventoried_canonical_keys() -> set[str]:
    """Canonical keys present in Stage 1/12 line inventory."""
    payload = load_json(LINE_INVENTORY_JSON)
    keys: set[str] = set()
    for line in payload.get("brand_line_inventory", []):
        if line.get("canonical_key"):
            keys.add(str(line["canonical_key"]))
    return keys


def active_override_groups() -> list[dict[str, Any]]:
    """
    Return line override groups whose canonical_key is active in Stage 12.

    Groups with requires_stage12_inventory_addition=true stay dormant until
    the canonical key has normalized shade records in Stage 12 section C.
    """
    shade_keys = stage12_canonical_keys_with_shades()
    active: list[dict[str, Any]] = []
    for group in load_line_overrides():
        canonical_key = str(group["canonical_key"])
        needs_inventory = bool(group.get("requires_stage12_inventory_addition"))
        if needs_inventory and canonical_key not in shade_keys:
            continue
        active.append(group)
    return active


def flatten_line_override_rules(*, include_dormant: bool = False) -> list[dict[str, Any]]:
    """Expand brand_line_overrides into flat rule rows tagged with canonical_key."""
    groups = load_line_overrides() if include_dormant else active_override_groups()
    rules: list[dict[str, Any]] = []
    for group in groups:
        canonical_key = group["canonical_key"]
        for rule in group.get("override_rules", []):
            enriched = dict(rule)
            enriched["canonical_key"] = canonical_key
            enriched["scope_level"] = "line"
            rules.append(enriched)
    return rules


def all_rule_ids() -> set[str]:
    """Collect every rule_id referenced in the package."""
    ids: set[str] = set()
    for rule in load_universal_rules():
        ids.add(rule["rule_id"])
    for group in load_line_overrides():
        for rule in group.get("override_rules", []):
            ids.add(rule["rule_id"])
    return ids


def clear_caches() -> None:
    """Clear loader caches (for tests)."""
    load_ontology.cache_clear()
    load_universal_rules.cache_clear()
    load_service_workflows.cache_clear()
    load_line_overrides.cache_clear()
    load_decision_order.cache_clear()
    load_validation_cases.cache_clear()
    load_conflicts_and_gaps.cache_clear()
    load_manifest.cache_clear()
    stage12_canonical_keys_with_shades.cache_clear()
    stage12_inventoried_canonical_keys.cache_clear()
