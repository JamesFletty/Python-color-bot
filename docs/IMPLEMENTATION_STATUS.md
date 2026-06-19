# Hair Color Formula Engine — Implementation Status

**Last updated:** 2026-06-19  
**Baseline commit:** current branch after CI/status-alignment documentation pass

This document evaluates what is **done**, what is **partial**, and what **remains** to reach a production-ready salon formula recommendation service. It supersedes informal backlog notes from the integration conversation.

---

## Executive summary

The project has two runnable stacks that share Stage 13 JSON rules but use different persistence layers:

| Stack | Status | Entry points |
|-------|--------|--------------|
| **Phase 1 SQLite** | **Operational** | `init_db.py`, `query_engine.py`, `formula_engine.py`, `api/main.py` (FastAPI) |
| **Production PostgreSQL** | **CLI + tests operational; no HTTP service** | `bootstrap.py`, `run_production_engine.py`, `query_production_engine.py` |

**Core engine behavior is implemented:** Stage 13 rule resolution, deposit/fill guidance, gray developer defaults, brand line overrides, cross-engine validation, auto sub-range from shade records, inventory-backed fill shade lookup on both SQLite and PostgreSQL engine outputs, and PostgreSQL shade search/matching.

**Primary gaps:** production HTTP API, rule/data coverage for unextracted lines (103+), Alembic migration project, broader static-analysis coverage, gram-age/consultation productization, and exposing the PostgreSQL parity output through an HTTP surface.

---

## Architecture (current)

```mermaid
flowchart TB
    subgraph Artifacts["Versioned JSON"]
        S12[stage12_package<br/>1828 shades]
        S13[stage13_formulation_rules<br/>18 universal + 14 line overrides]
    end

    subgraph SQLite["Phase 1 — SQLite"]
        INIT[init_db.py]
        DB[(hair_color.db)]
        QUERY[query_engine.py]
        FORM[formula_engine.py]
        API[api/main.py<br/>GET /health POST /formula]
        FILL[src/fill_shade_lookup.py]
    end

    subgraph PG["Production — PostgreSQL"]
        MIG[migrate.py]
        BOOT[bootstrap.py]
        PGDB[(PostgreSQL)]
        RUN[run_production_engine.py]
        QPG[query_production_engine.py]
        ENG[run_engine + SqlAlchemyEngineRepository]
        PERSIST[persist.py]
    end

    subgraph Shared["Shared logic"]
        RES[stage13 resolver]
        EVAL[formulation_rules/evaluator.py]
        SVC[src/formula_engine_service.py]
    end

    S12 --> INIT --> DB
    S12 --> BOOT --> PGDB
    S13 --> RES
    S13 --> ENG
    EVAL --> RES
    EVAL --> ENG
    DB --> QUERY
    DB --> FORM
    DB --> FILL
    SVC --> FORM
    SVC --> API
    MIG --> PGDB
    BOOT --> PGDB
    PGDB --> RUN --> ENG
    PGDB --> QPG
    ENG --> PERSIST --> PGDB
```

---

## Completed work

### Stage 12 — Research data (partial inventory)

| Item | Status | Evidence |
|------|--------|----------|
| 30 lines with shade extraction | Done | `stage12_package/MANIFEST.json` |
| 1,828 normalized shade records | Done | `C_normalized_shade_records.json`, `init_db.py` verification |
| 659 tone normalization mappings | Done | `F_tone_normalization_map.json` |
| 28 line technical records | Done | `D_line_technical_records.json` |
| Batches 01–07 integrated | Done | `hair_color_db/batches/batch01` … `batch07` |
| Gap / licensing reports | Done | `stage11_gaps/`, `stage12_package/I_gap_risk_licensing_report.json` |

### Stage 13 — Formulation rules

| Item | Status | Evidence |
|------|--------|----------|
| 18 universal rules (U001–U018) | Done | `B_universal_rule_library.json`, `MANIFEST.json` |
| 14 active line override groups | Done | `D_brand_line_overrides.json` |
| 9 service workflows | Done | `C_service_workflows.json` |
| 20 validation cases (VC001–VC029 subset) | Done | `F_validation_cases.json` |
| Deterministic resolver | Done | `resolver.py` |
| Deposit/fill and lift precedence rules (U013–U018) | Done | gray 20 vol, deposit 10 vol, fill pigment, 20/30/40 lift developer locks |
| Brand gray overrides (Koleston, Topchic, IGORA, Majirel, Kenra, Colorance, Matrix collections) | Done | `D_brand_line_overrides.json` |
| Shared rule evaluator | Done | `hair_color_db/formulation_rules/evaluator.py` (PR #14) |
| Package build / emit | Done | `build.py`, `emit_artifacts.py` |

### Phase A–E integration (merged PR #15)

| Stage | Description | Key modules |
|-------|-------------|-------------|
| **B** | Stage 13 → PostgreSQL import | `import_stage13_rules.py` |
| **C** | Cross-engine validation CI | `cross_engine_validation.py`, `test_cross_engine_validation.py` |
| **D** | Stage 12 → PostgreSQL import | `import_stage12_research.py` |
| **E** | SQLite CLI convergence | `src/formula_builder.py`, `formula_engine.py`, Stage 13 overlay on primary `developer` |

### Post-integration features (PRs #16–#19 + recent stabilization)

| Feature | PR | Notes |
|---------|-----|-------|
| PostgreSQL e2e wiring | #16 | `db.py`, `migrate.py`, `bootstrap.py`, `persist.py`, `docker-compose.yml` |
| PostgreSQL shade search/matching | #17 | `shade_matching.py`, `query_production_engine.py`, `--shade-ref` |
| Auto sub-range from shade record | #18 | `src/sub_range_intake.py`; no manual `--sub-range` for collection shades |
| FastAPI over SQLite engine | #19 | `api/main.py`, `src/formula_engine_service.py` |
| CI + PG test baseline | Recent | `.github/workflows/ci.yml`, `pyproject.toml`, `pg_test_utils.py` |
| Cross-engine warning status alignment | Recent | warning-only actions resolve to `caution` in both Stage 13 and production |

### SQLite CLI capabilities

- Shade search by level/tone/brand/gray (`query_engine.py`)
- Formula build with Stage 13 rules, fill guidance, inventory `suggested_shades` (`formula_engine.py`)
- Three-part shade refs `Brand::Line::Code` with line hint disambiguation
- `--sub-range` override; auto-detect when omitted
- `--existing-level`, `--desired-level`, `--service-intent`, patch test gate

### Production engine capabilities

- `run_engine()` with repository injection (in-memory + SQLAlchemy)
- Intermixing, color science, line technical defaults, risk assessments
- `persistence_payload` + `persist.py` writer for formula/steps/risks
- Fill pigment step in output with PostgreSQL inventory enrichment
- Auto `selected_sub_ranges` from `SelectedShade.sub_range_name`

---

## Test coverage matrix

| Suite | Requires | Approx. tests | Command |
|-------|----------|---------------|---------|
| Production engine golden paths | nothing | ~24 | `python3 -m unittest hair_color_db.production.test_engine -v` |
| Stage 13 import rows | nothing | ~10 | `python3 -m unittest hair_color_db.production.test_import_stage13_rules -v` |
| Cross-engine validation | nothing | 3 (+20 cases) | `python3 -m unittest hair_color_db.production.test_cross_engine_validation -v` |
| Stage 13 resolver validation | nothing | 22 | `python3 hair_color_db/stage13_formulation_rules/test_stage13_validation.py` |
| Deposit/fill rules | nothing / SQLite | ~11 | `python3 -m unittest hair_color_db.stage13_formulation_rules.test_deposit_fill_rules -v` |
| Sub-range intake | nothing / SQLite | ~8 | `python3 -m unittest src.test_sub_range_intake -v` |
| Formula builder Stage 13 | `init_db.py` | ~9 | `python3 -m unittest src.test_formula_builder -v` |
| Fill shade lookup | `init_db.py` | 2 | `python3 -m unittest src.test_fill_shade_lookup -v` |
| FastAPI | `init_db.py` | 3 | `python3 -m unittest api.test_api -v` |
| PostgreSQL e2e | `DATABASE_URL` + bootstrap | 3 | `python3 -m unittest hair_color_db.production.test_pg_e2e -v` |
| PG shade matching parity | `DATABASE_URL` + SQLite | 4 | `python3 -m unittest hair_color_db.production.test_pg_shade_matching -v` |
| Stage 12 PG import | `DATABASE_URL` | 4 | `python3 -m unittest hair_color_db.production.test_import_stage12_research -v` |

**Recommended smoke (no external services):**

```bash
pip install -r requirements.txt
python3 init_db.py
PYTHONPATH=. python3 -m unittest \
  hair_color_db.production.test_engine \
  hair_color_db.production.test_cross_engine_validation \
  hair_color_db.stage13_formulation_rules.test_stage13_validation \
  src.test_formula_builder \
  api.test_api -v
```

---

## Remaining work

Work items are grouped by priority. Each includes acceptance criteria and primary touchpoints.

### Tier 1 — Production readiness & engine parity

These unblock a single production deployment path with behavior matching the SQLite reference implementation.

#### R1.1 — Production HTTP API

**Status:** Baseline complete. The FastAPI app can run against SQLite or PostgreSQL with `ENGINE_BACKEND=sqlite|postgres`; PostgreSQL mode uses `run_production_engine()` and reports database/import readiness through `/health`.

**Scope:**
- `POST /formula` is backed by `run_production_engine` + `SqlAlchemyEngineRepository` when `ENGINE_BACKEND=postgres`
- `api/schemas.py` now carries the extra production fields needed by PostgreSQL (`elasticity`, `texture`, `desired_result`, `recommendation_type`, `persist`)
- `/health` checks `DATABASE_URL`, DB connectivity, Stage 12 shade count, and active Stage 13 formulation rules

**Acceptance criteria:**
- PG-backed API returns the same production-engine payload shape and developer volume source as `run_production_engine.py`
- Health endpoint reports PG connectivity and import readiness (shade count ≥ 1828, active Stage 13 rules > 0)

**Depends on:** PostgreSQL bootstrap (done)

**Files:** `api/main.py`, `api/schemas.py`, `api/test_production_api.py`

---

#### R1.2 — PostgreSQL fill shade inventory enrichment

**Status:** Complete for engine output. Production `run_engine()` now enriches computed fill guidance with PostgreSQL inventory-backed `suggested_shades` and `target_natural_shades`; PG e2e coverage exercises a 9→5 Matrix darkening case.

**Remaining product work:** Keep SQLite/PG parity cases in CI and decide how much of the enriched guidance should be considered stable public API.

---

#### R1.3 — Cross-engine warning → status alignment

**Status:** Complete. Warning-only rule actions now resolve to `caution` in both engines; `test_cross_engine_validation` no longer carries a warning-elevation exemption list.

**Current policy:** Stage 13 and production both treat emitted formulation warnings as formula-safe cautions. Hard stops and consultation gates still take precedence over caution.

**Regression coverage:** All 20 packaged validation cases compare `recommendation_status`, matched rules, developer volume, and block/workflow fields through `test_cross_engine_validation.py`.

**Next action:** Keep this item closed unless a new, named divergence is introduced with an explicit design note and validation case.

---

#### R1.4 — Unified API routing (SQLite vs PostgreSQL)

**Status:** Baseline complete via `ENGINE_BACKEND=sqlite|postgres`. The same `/health` and `/formula` routes dispatch to the selected backend.

**Scope:**
- Optional future versioned routers (`/v1/sqlite/*`, `/v1/production/*`) if both backends must be served simultaneously
- OpenAPI polish for backend-specific readiness details and persistence behavior

**Acceptance criteria:**
- One `uvicorn` process can serve either backend via configuration
- Health response identifies the active backend and reports backend-specific readiness

**Depends on:** R1.1

---

### Tier 2 — Rule engine completeness

#### R2.1 — G005: Pulp Riot FACTION8 line override

**Status:** Open (`G_conflicts_and_gaps.json`)

**Gap:** Permanent FACTION8 line has no Stage 13 override group; only semi-permanent covered by U009.

**Scope:**
- Add override group to `D_brand_line_overrides.json` when permanent formulation rules are scoped
- Requires FACTION8 shade inventory in Stage 12 (currently in Stage 11 gap queue)

**Acceptance criteria:**
- New validation case VC0xx for FACTION8 permanent service path
- Override group active (not dormant) once shades exist in section C

**Depends on:** Stage 12 extraction for Pulp Riot FACTION8 (Tier 4)

**Files:** `D_brand_line_overrides.json`, `F_validation_cases.json`, `emit_artifacts.py`

---

#### R2.2 — Apply `developer_override` intermixing rules

**Status:** Complete for developer-volume overrides. Intermixing rules with `restriction_type=developer_override` can now adjust developer selection when their restriction note specifies a salon volume such as `10 vol`, unless a formulation rule has explicitly locked developer volume.

**Remaining product work:** Add real imported `developer_override` data when manufacturer line charts require it; current coverage uses seeded/unit fixtures.

---

#### R2.3 — Reserved validation cases

**Status:** VC002, VC014–VC018, VC020–VC022 reserved (`MANIFEST.json`)

**Scope:** Author cases when corresponding lines/batches land (e.g. Illumina, Color Fusion, additional Goldwell sub-ranges)

**Acceptance criteria:** Each new batch adds ≥1 validation case before merge

---

#### R2.4 — `formula_zones` in production output

**Status:** Complete for engine output. Production `EngineOutput` now surfaces workflow formula zones for `WF_retouch_with_refresh`, and cross-engine validation compares those zones directly.

**Remaining product work:** Decide whether future API responses should expose zones as top-level metadata only, step zoning only, or both.

---

### Tier 3 — Platform, schema & operations

#### R3.1 — CI test pipeline

**Status:** Baseline complete. `.github/workflows/ci.yml` runs on push and pull requests with Python 3.12, a `postgres:15` service, SQLite catalog initialization, `ruff`, focused `mypy`, unit suites, and PostgreSQL integration tests.

**Remaining hardening:**
- Split lint/type, SQLite, and PostgreSQL checks into separate jobs for clearer failure reporting.
- Expand `ruff` beyond correctness-only rules after cleanup.
- Expand mypy targets beyond focused engine modules once current type debt is addressed.
- Add CI artifacts/log upload and an optional README badge.

---

#### R3.2 — Alembic project (replace manual migration runner)

**Status:** Revision modules exist as copy-paste artifacts; `migrate.py` runs SQL files with `schema_migration` table

**Scope:**
- Add `alembic.ini`, `alembic/env.py` pointing at existing revisions
- Keep `bootstrap.py` calling Alembic upgrade head

**Acceptance criteria:** Fresh DB via `alembic upgrade head` equivalent to current `migrate.py` + seeds

**Files:** `hair_color_db/production/alembic_revision*.py`, new `alembic/` directory

---

#### R3.3 — Gram-age / quantity module

**Status:** 60g placeholders everywhere (`engine_readme.md`)

**Scope:** Replace fixed `quantity_grams` with hair-length or stylist-input-driven defaults

**Acceptance criteria:** Formula steps include documented quantity rationale; tests for at least short/medium/long hair

---

#### R3.4 — Consultation / auth layer

**Status:** `persist.py` creates stub consultations with `SYSTEM_STYLIST_ID`

**Scope:** Auth middleware, real stylist/salon IDs, consultation lifecycle before formula persist

**Depends on:** R1.1 production API

---

#### R3.5 — Schema extension H — evidence tables

**Status:** Proposed in `H_schema_extension_proposal.json`; partial (workflows + validation_case imported; `formulation_rule_evidence` not wired)

**Scope:** Import evidence links from Stage 13 package; expose in rule audit trail

---

### Tier 4 — Data acquisition backlog

Not blocking engine runtime for **currently extracted** 30 lines, but limits brand coverage and dormant override activation.

| Metric | Count | Source |
|--------|-------|--------|
| Lines inventoried | 133 | Stage 1 |
| Lines with shade extraction | 30 | Stage 12 MANIFEST |
| Lines queued (gaps) | 103+ | `stage11_gaps/gap_risk_report.json` |
| Formulation gaps | 1 (G005) | `G_conflicts_and_gaps.json` |

**High-value extraction targets** (examples from gap reports):
- Pulp Riot FACTION8, Liquid Demi, Lighteners
- Redken Color Fusion, Shades EQ Cream
- Wella Illumina, Blondor lighteners
- Schwarzkopf IGORA variants beyond ROYAL/VIBRANCE

**Process per batch:** Stages 4–9 tools → integrate into `stage12_package` → `init_db.py` / PG import → new line overrides + validation cases.

---

## Doc & code hygiene (quick fixes)

| Item | Location | Fix |
|------|----------|-----|
| Stale shade count in init header | `init_db.py` | Update 1,479 → 1,828 |
| I_integration_notes case count | keep in sync with MANIFEST | 20 validation cases |
| Stage 13 universal rule range in I_integration_notes | keep in sync with MANIFEST | U001–U018 |
| Static-analysis scope | `pyproject.toml` / CI | expand ruff and mypy coverage incrementally |

---

## Recommended implementation sequence

For a **production MVP** (salon-facing API on PostgreSQL with parity to SQLite CLI):

```
1. R3.2  Alembic project                   ← ops maturity for the PG-backed service
2. R3.1  CI/static-analysis expansion      ← broaden beyond the baseline gate
3. R3.3  Gram-age module                   ← professional quantity rationale
4. R3.4  Consultation/auth layer           ← production workflow ownership
5. API v1 response contract                ← freeze public PG response fields
6. T4    Data/rule expansion               ← broader brand and line coverage
```

For **coverage expansion** (parallel track):

```
T4 batches → R2.1 G005 / FACTION8 → R2.3 new validation cases
```

---

## Reference — merged PR history

| PR | Feature |
|----|---------|
| #14 | Shared rule evaluator |
| #15 | Integration stack (Stages B–E, deposit/fill, `--sub-range`) |
| #16 | PostgreSQL e2e wiring |
| #17 | PostgreSQL shade search/matching |
| #18 | Auto sub-range from shade record |
| #19 | FastAPI over SQLite formula engine |

---

## Related documents

| Document | Path |
|----------|------|
| Data acquisition overview | `hair_color_db/README.md` |
| Production engine design | `hair_color_db/production/engine_readme.md` |
| Research vs production schema | `hair_color_db/production/research_vs_production_schema.md` |
| Stage 13 integration notes | `hair_color_db/stage13_formulation_rules/I_integration_notes.md` |
| Stage 12 package manifest | `hair_color_db/stage12_package/MANIFEST.json` |
| Stage 13 package manifest | `hair_color_db/stage13_formulation_rules/MANIFEST.json` |
| Formulation gaps | `hair_color_db/stage13_formulation_rules/G_conflicts_and_gaps.json` |
| Local PostgreSQL setup | `.env.example`, `docker-compose.yml` |
