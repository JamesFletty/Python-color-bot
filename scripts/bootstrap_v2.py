#!/usr/bin/env python3
"""Apply v2 Alembic migrations and seed PostgreSQL from CSV artifacts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    steps = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [sys.executable, "scripts/seed_db.py"],
    ]
    for cmd in steps:
        print(f"Running: {' '.join(cmd)}", file=sys.stderr)
        result = subprocess.run(cmd, cwd=repo_root, env=env)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
