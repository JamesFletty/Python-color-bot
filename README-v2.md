# ColorSynth Formula Engine — v2

This branch introduces the **v2 simplified architecture** described in
[`prd/colorsynth-formula-engine-v2.md`](prd/colorsynth-formula-engine-v2.md).

v1 (`api/`, `src/`, `hair_color_db/production/`) remains intact during the migration.
v2 code lives alongside it until Phase 5 cleanup.

## Status (Phase 4)

| Deliverable | Status |
|-------------|--------|
| Phases 1–3 (data, engine, API) | Done |
| Frontend wired to v2 API (`/brands`, `/lines`, `/formula`, `/ai/*`) | Done |
| `pnpm` only (removed `package-lock.json`) | Done |
| Deleted `artifacts/mockup-sandbox/` | Done |
| `static/dist/` gitignored (build via `pnpm build`) | Done |
| v1 deletion | Phase 5 |

## Frontend dev

```bash
# Terminal 1 — backend (requires Postgres + seed)
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor
PYTHONPATH=/workspace python3 scripts/bootstrap_v2.py
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Vite dev server (proxies API to :8000)
cd frontend && pnpm dev:frontend

# Or both together:
cd frontend && pnpm dev
```

Production build (served by FastAPI at `/` when `static/dist/` exists):

```bash
cd frontend && pnpm build
```

## API endpoints (v2)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | DB + LLM readiness |
| GET | `/brands` | Brand/line catalog |
| GET | `/lines/{line_id}/shades` | Shades for a line |
| POST | `/formula` | Deterministic formula engine |
| POST | `/ai/parse` | NL → structured params (LLM or deterministic fallback) |
| POST | `/ai/translate` | Cross-line translate + formula (requires LLM) |
| POST | `/ai/explain` | Explain formula output (requires LLM) |

Swagger UI: `/docs`

## Phase 2 commands

```bash
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor

# Migrate + seed (requires running postgres)
PYTHONPATH=/workspace python3 scripts/bootstrap_v2.py

# Run v2 test suite
PYTHONPATH=/workspace python3 -m unittest discover -s tests/v2 -v
```

## Phase 1 commands

```bash
# Audit source JSON (counts, duplicates, gaps)
PYTHONPATH=/workspace python3 scripts/audit_stage_data.py

# Export seed CSVs from stage12/stage13 JSON
PYTHONPATH=/workspace python3 scripts/export_stage12_to_csv.py
PYTHONPATH=/workspace python3 scripts/export_stage13_to_csv.py
PYTHONPATH=/workspace python3 scripts/export_crossline_to_csv.py

# Validate exports
PYTHONPATH=/workspace python3 -m unittest tests.v2.test_export_validation -v
```

## Inventory (repo-verified)

- **2,537** normalized shades (stage12 `C_normalized_shade_records.json`)
- **1,032** cross-line conversion entries
- **36** formulation rules (18 universal + 18 line overrides)
- **136** brand/line inventory rows

## v2 stack

- Python 3.12 + FastAPI
- PostgreSQL 16 (single backend — no `ENGINE_BACKEND` switch)
- OpenAI SDK with configurable `OPENAI_BASE_URL` (Bedrock Mantle compatible)
- React 18 + Vite frontend (existing `frontend/`, cleaned in Phase 4)

## Run v2 API scaffold

```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health: `GET /health`
