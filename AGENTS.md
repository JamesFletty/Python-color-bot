# AGENTS.md

## Cursor Cloud specific instructions

This is a single Python (3.12) product: a professional hair-color database + deterministic
formula engine. There are two parallel tracks that share the same Stage 12/13 JSON data:

- **Phase 1 (SQLite)** — `init_db.py`, `query_engine.py`, `formula_engine.py`, and the
  FastAPI app in `api/`. This is the runnable application and needs no external services.
- **Production (PostgreSQL)** — `hair_color_db/production/*`. Backed by the `postgres:15`
  container in `docker-compose.yml`. See `hair_color_db/production/engine_readme.md` for the
  authoritative command list.

Dependencies are installed by the startup update script (`pip install -r requirements.txt`,
into `~/.local`). The notes below are the non-obvious bits not covered by that script or the
existing docs.

### Phase 1 / FastAPI (no external services)

- The SQLite DB (`hair_color.db`) is git-ignored and is NOT created by the update script.
  Build it before running the API or the SQLite-track e2e tests: `python3 init_db.py`
  (writes `hair_color.db` + `hair_color_db_verification_report.json`; expects 1,828 shades).
- Run the API in dev mode: `python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000`
  (the `uvicorn` console script lands in `~/.local/bin`, which is not on `PATH`; invoke via
  `python3 -m uvicorn`). Swagger UI is at `/docs`; health at `/health`; build a formula via
  `POST /formula` (e.g. `{"shade":"Matrix::SoColor::5N","gray":60,"service_intent":"gray_coverage"}`).

### Running tests

- Tests use stdlib `unittest` (no pytest). Run from the repo root so imports resolve.
- Scripts run directly (not as `-m`) need the repo root on the path, e.g.
  `PYTHONPATH=/workspace python3 hair_color_db/stage13_formulation_rules/test_stage13_validation.py`.
- No linter/type-checker is configured (none in `requirements.txt`); `python3 -m compileall`
  is a reasonable syntax sanity check.
- `test_pg_e2e.py` / `test_pg_shade_matching.py` self-skip unless `DATABASE_URL` is set.

### Production / PostgreSQL track

- Docker is installed in the VM snapshot but the daemon is NOT auto-started. Start it once per
  session (no systemd here): `sudo dockerd &` (it uses the `fuse-overlayfs` storage driver with
  `containerd-snapshotter` disabled via `/etc/docker/daemon.json` — required for Docker 29 in
  this VM). Then `sudo docker compose up -d` starts `postgres:15` on `localhost:5432`
  (user/pass/db all `haircolor`). `docker` requires `sudo`.
- Export the connection string before bootstrap/CLIs/tests:
  `export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor`.
- Bootstrap (idempotent): `python3 -m hair_color_db.production.bootstrap` runs
  migrate → Stage 12 research import → Stage 13 rules import. Expect `status: ok`,
  1,828 shades, and exit code 0. The `test_pg_*` and `test_import_stage12_research`
  integration tests self-skip unless `DATABASE_URL` is set, and each re-bootstraps in
  `setUpClass` (so they take ~1–3 min total; the import re-runs are idempotent).
- To re-bootstrap from a clean slate, reset the schema first:
  `sudo docker exec workspace-postgres-1 psql -U haircolor -d haircolor -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO haircolor;"`
- Non-obvious: Matrix SoColor intermixing rules are seeded by
  `import_stage12_research.import_intermixing_rules` (SQL in `seed_intermixing_rules.sql`),
  NOT by the migration — they are `INSERT … SELECT` against research tables and must run
  after the Stage 12 import. Only sub-ranges present in the data seed rows (currently
  `DreamAge` + `Pre-Bonded 10 min`).
- Non-obvious: `stage12_report.tone_mapping_count` is the count of source tone-map
  entries (659); the normalized `tone_normalization` table holds many more rows
  (surfaced as `tone_normalization_link_count`), because each entry expands into one
  row per (tone_code, normalized_tone) plus synthetic links added during shade import.
