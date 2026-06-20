#!/usr/bin/env python3
"""Convert v4 Wella / Matrix / L'Oréal seed package expansion to Stage 12 batch artifacts."""

from __future__ import annotations

import json
import os
import sys

TOOLS = os.path.dirname(__file__)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from seed_package_builder import build_batch_artifacts, line_key, write_batch_artifacts
from seed_package_mappings import BATCH10_BRANDS, BATCH10_LINE_KEYS

BASE = os.path.join(TOOLS, "..")
B10 = os.path.join(BASE, "batches", "batch10")
SEED_PATH = os.path.join(B10, "seed_package.json")


def shade_filter(shade: dict) -> bool:
    return line_key(shade["brand"], shade.get("product_line")) in BATCH10_LINE_KEYS


def rule_filter(rule: dict) -> bool:
    return rule["brand"] in BATCH10_BRANDS


def main() -> None:
    with open(SEED_PATH, encoding="utf-8") as handle:
        pkg = json.load(handle)
    artifacts = build_batch_artifacts(
        pkg,
        batch_number=10,
        batch_label="batch10",
        shade_filter=shade_filter,
        rule_filter=rule_filter,
    )
    write_batch_artifacts(B10, artifacts, 10)
    print(json.dumps(artifacts["manifest"], indent=2))


if __name__ == "__main__":
    main()
