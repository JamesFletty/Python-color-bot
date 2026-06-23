# ColorSynth Formula Engine — v2

This branch is the **v2 simplified architecture** described in
[`prd/colorsynth-formula-engine-v2.md`](prd/colorsynth-formula-engine-v2.md).

v1 code (`api/`, `src/`, `hair_color_db/production/`) has been removed. The runnable
application is `app/` with PostgreSQL only.

## Status (Phase 5 complete)

| Deliverable | Status |
|-------------|--------|
| Phases 1–4 (data, engine, API, frontend) | Done |
| v1 deletion + Docker/CI cleanup | Done |
| Single LLM provider (`LLM_*` env vars) | Done |

## Quick start

```bash
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor

# Migrate + seed (requires running postgres)
PYTHONPATH=. python3 scripts/bootstrap_v2.py

# Run API (serves built frontend from static/dist/ when present)
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Docker full stack (builds frontend + bootstraps on start):

```bash
docker compose up --build
```

## Frontend dev

```bash
# Terminal 1 — backend
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor
PYTHONPATH=. python3 scripts/bootstrap_v2.py
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

## API endpoints

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

## Tests

```bash
PYTHONPATH=. python3 -m unittest discover -s tests/v2 -v
```

## Regenerate seed CSVs

```bash
PYTHONPATH=. python3 scripts/audit_stage_data.py
PYTHONPATH=. python3 scripts/export_stage12_to_csv.py
PYTHONPATH=. python3 scripts/export_stage13_to_csv.py
PYTHONPATH=. python3 scripts/export_crossline_to_csv.py
PYTHONPATH=. python3 -m unittest tests.v2.test_export_validation -v
```

## Inventory (repo-verified)

- **2,537** normalized shades
- **1,032** cross-line conversion entries
- **143** formulation rules (18 universal + 125 line overrides)
- **136** brand/line inventory rows

## Stack

- Python 3.12 + FastAPI
- PostgreSQL 15+ (single backend)
- OpenAI SDK with `LLM_BASE_URL` (Bedrock Mantle compatible)
- React 18 + Vite frontend
