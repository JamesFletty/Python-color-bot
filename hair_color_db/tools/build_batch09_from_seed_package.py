#!/usr/bin/env python3
"""Convert normalized seed package (v3 Aveda Full Spectrum expansion) to Stage 12 batch artifacts."""

from __future__ import annotations

import json
import os
import sys

TOOLS = os.path.dirname(__file__)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from seed_package_builder import build_batch_artifacts, write_batch_artifacts

BASE = os.path.join(TOOLS, "..")
B9 = os.path.join(BASE, "batches", "batch09")
SEED_PATH = os.path.join(B9, "seed_package.json")


def main() -> None:
    with open(SEED_PATH, encoding="utf-8") as handle:
        pkg = json.load(handle)
    artifacts = build_batch_artifacts(
        pkg,
        batch_number=9,
        batch_label="batch09",
    )
    write_batch_artifacts(B9, artifacts, 9)
    print(json.dumps(artifacts["manifest"], indent=2))


if __name__ == "__main__":
    main()
