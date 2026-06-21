#!/bin/sh
set -eu

if [ "${BOOTSTRAP_ON_START:-0}" = "1" ] && [ -n "${DATABASE_URL:-}" ]; then
  echo "Running PostgreSQL bootstrap..."
  python3 -m hair_color_db.production.bootstrap
fi

exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
