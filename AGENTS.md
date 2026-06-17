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

- KNOWN PRE-EXISTING BUG (blocks the PostgreSQL track): `hair_color_db/production/migrate.py`
  `_statements()` splits SQL on every `;`, which breaks the dollar-quoted `set_updated_at()`
  function body in `production_operational_schema.sql`. As a result
  `python3 -m hair_color_db.production.bootstrap` (and the `test_pg_*` e2e tests, which call it)
  fail with `unterminated dollar-quoted string`. This is an application-code defect, not an
  environment problem; the Postgres service itself is healthy. The production engine *logic* is
  fully exercised by the in-memory test suite (`test_engine`, `test_import_*`,
  `test_cross_engine_validation`) which does not touch Postgres.
