#!/usr/bin/env python3
"""Apply v2 Alembic migrations and seed PostgreSQL from CSV artifacts."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    env = {"PYTHONPATH": "/workspace"}
    import os

    merged = os.environ.copy()
    merged.update(env)

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    steps = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "scripts/seed_db.py"],
    ]
    for cmd in steps:
        print(f"Running: {' '.join(cmd)}", file=sys.stderr)
        result = subprocess.run(cmd, cwd="/workspace", env=merged)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
