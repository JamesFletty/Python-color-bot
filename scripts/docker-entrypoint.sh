#!/bin/sh
set -eu

if [ "${BOOTSTRAP_ON_START:-0}" = "1" ] && [ -n "${DATABASE_URL:-}" ]; then
  echo "Running v2 PostgreSQL bootstrap..."
  python3 scripts/bootstrap_v2.py
fi

exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
