# AGENTS.md

## Cursor Cloud specific instructions

ColorSynth Formula Engine **v2** — a single Python (3.12) FastAPI app backed by PostgreSQL.

- **Application:** `app/` (FastAPI + deterministic formula engine)
- **Seed data:** `data/seed/*.csv` (generated from Stage 12/13 JSON via `scripts/export_*.py`)
- **Source JSON:** `hair_color_db/stage12_package/`, `hair_color_db/stage13_formulation_rules/`
- **Frontend:** `frontend/` (React + Vite; build output in `static/dist/`)

Dependencies install via `pip install -r requirements.txt` into `~/.local`.

### Local development

1. Start Postgres: `sudo dockerd &` then `sudo docker compose up -d postgres`
2. Export: `export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor`
3. Bootstrap: `PYTHONPATH=. python3 scripts/bootstrap_v2.py`
4. Run API: `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Swagger UI at `/docs`; health at `/health`

Expected inventory after seed: **2,537 shades**, **143 rules**, **1,032 cross-line mappings**
(`scripts/v2_paths.py` `EXPECTED_SHADE_COUNT`).

### LLM routes

- `POST /ai/parse` — deterministic fallback when no LLM key configured
- `POST /ai/translate`, `POST /ai/explain` — require `LLM_API_KEY` (503 without it)
- Configure via `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_CHAT_MODEL`, `LLM_TRANSLATE_MODEL`

### Running tests

Tests use stdlib `unittest` (no pytest). Run from repo root:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests/v2 -v
```

PostgreSQL integration tests need `DATABASE_URL` set and bootstrap run first.

### Docker full stack

`sudo docker compose up --build` bootstraps on start (`BOOTSTRAP_ON_START=1`) and serves
`app.main:app` on port 8000 with the built frontend SPA.

See [`README-v2.md`](README-v2.md) for export/regeneration commands.
