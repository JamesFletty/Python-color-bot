# Deterministic Formula Engine

Execution layer that consumes the operational production schema and produces auditable formula recommendations.

## Module map

| Module | Responsibility |
|---|---|
| `engine_models.py` | Input/output contracts, evaluation context, accumulated action state |
| `repositories.py` | `EngineRepository` protocol, SQLAlchemy + in-memory loaders |
| `rule_evaluator.py` | Condition evaluation, rule matching, action application |
| `safety_checks.py` | Intermixing, color science, line technical defaults, risk drafts |
| `formula_builder.py` | Step assembly, `run_engine()` orchestrator, persistence payloads |
| `import_stage13_rules.py` | Stage 13 JSON → PostgreSQL import (formulation rules, workflows, validation cases) |
| `test_engine.py` | 22 golden-path and edge-case unit tests |
| `cross_engine_validation.py` | Stage 13 resolver vs production `run_engine()` comparison helpers |
| `import_stage12_research.py` | Stage 12 JSON → PostgreSQL research tables (shades, tones, line technical) |
| `test_import_stage12_research.py` | Stage 12 import regression + engine e2e with catalog UUIDs |

## Execution order

1. Resolve `brand_id` from `line_id` when not supplied on input.
2. Build `RuleEvaluationContext` (includes computed `lift_levels`).
3. Load applicable active `formulation_rule` rows.
4. Evaluate conditions → sort by scope tier then `rule_priority` → apply actions.
5. Merge `line_technical_rule` typed defaults (JSON fallback only when typed absent).
6. Run `shade_intermixing_rule` checks on selected shades.
7. Run `universal_color_science` lift/pigment realism checks.
8. Derive `recommendation_status`.
9. Assemble `suggested_formula` steps (skipped when blocked or consultation-required).
10. Build `risk_assessment` drafts and optional `persistence_payload`.

## Precedence / conflict resolution

| Priority | Rule |
|---|---|
| 1 | **Applicability filter** — line rows restrict to `line_id`; brand rows to `brand_id`; empty join tables = universal |
| 2 | **Condition match** — `all_of` must all pass; `any_of` needs ≥1 pass; empty groups = pass |
| 3 | **Application order** — universal → brand → line (ascending scope rank), then ascending `rule_priority` within tier |
| 4 | **Scalar conflicts** — later-applied rule wins for `set_developer_volume`, processing time |
| 5 | **Risk modifiers** — `risk_modifier` / `increase_risk_score` **accumulate** (sum per risk key) |
| 6 | **Workflows** — `trigger_workflow` → `requires_consultation`; no auto-formula for `color_correction` |
| 7 | **Intermixing** — `not_mixable` → `blocked`; `caution` → warning only |
| 8 | **Line technical** — fills defaults only where formulation rules left gaps |

## Missing-field behavior

| Construct | Behavior |
|---|---|
| Field absent / `None` | Comparisons fail except `exists` / `is_not_null` |
| `existing_level` null | Treated as `natural_level` for lift calculation |
| `desired_level` null | Lift = 0 unless `existing_level` used in cross-field predicate |
| Empty `selected_shades` | Intermixing skipped; formula steps may lack shade IDs |
| `line_region_id` null | Skips intermixing + line technical repository loads |

## Supported condition operators

`=`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `exists`, `is_not_null`, `not_exists`

Cross-field references: when `value` is `"existing_level"`, `"natural_level"`, or `"desired_level"`, the comparator resolves that field from context.

## Recommendation statuses

| Status | Meaning |
|---|---|
| `ok` | Formula generated; persist if steps present |
| `caution` | Formula may be generated with warnings |
| `requires_consultation` | Workflow gate (lift >4, color correction); no persistence payload |
| `blocked` | Hard stop (intermixing violation); no formula |

## Usage

```python
from hair_color_db.production.formula_builder import run_engine
from hair_color_db.production.repositories import build_seed_repository

repo = build_seed_repository()
result = run_engine(engine_input, repo)
```

Production:

```python
from sqlalchemy.orm import Session
from hair_color_db.production.repositories import SqlAlchemyEngineRepository

repo = SqlAlchemyEngineRepository(session)
result = run_engine(engine_input, repo, line_region_id=region_id)
```

### Stage 13 rule import

After applying `alembic_revision_op002_stage13.py` (or the matching section of
`production_operational_schema.sql`), load the Stage 13 package into PostgreSQL:

```bash
export DATABASE_URL=postgresql+psycopg2://user:pass@host/db
python3 -m hair_color_db.production.import_stage13_rules
```

The import is idempotent (upserts on `package_rule_id`, `workflow_id`, `case_id`).
`build_seed_repository()` uses the same import logic for in-memory tests.

### Stage 12 research import

After applying `alembic_revision_research_baseline.py` (or `research_baseline_schema.sql`):

```bash
export DATABASE_URL=postgresql+psycopg2://user:pass@host/db
python3 -m hair_color_db.production.import_stage12_research
```

Loads 1,828 shades, 659 tone mappings, and line technical rules from `stage12_package/`.
Shade UUIDs are deterministic (`uuid5` on canonical key + sub-range + shade code).
`SqlAlchemyEngineRepository` reads imported research rows for line technical rules and shades.

## Assumptions

- `formula` stores `line_id` only; brand derived at read time.
- Shade selection can be supplied via `--shade-ref` lookup or explicit catalog IDs on input.
- Quantity grams are planned from `hair_length` (`short`, `medium`, `long`, `extra_long`) and surfaced with a quantity rationale.
- Research tables are read-only through repositories.

## Known limitations

- The FastAPI service can expose PostgreSQL output with `ENGINE_BACKEND=postgres`; versioned public response contracts are still pending.
- `run_engine()` does not persist — use `persist.persist_engine_output()` or `run_production_engine --persist`.
- Single primary line per recommendation (no multi-line formulas).
- JSON `rule_value` fallback parsing is intentionally narrow (developer volume, mixing ratio string).

## Running tests

```bash
pip install -r requirements.txt
python3 -m unittest hair_color_db.production.test_engine -v
python3 -m unittest hair_color_db.production.test_import_stage13_rules -v
python3 -m unittest hair_color_db.production.test_import_stage12_research -v
python3 -m unittest hair_color_db.production.test_cross_engine_validation -v
python3 hair_color_db/stage13_formulation_rules/test_stage13_validation.py
```

PostgreSQL end-to-end (requires `DATABASE_URL`):

```bash
docker compose up -d
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor
python3 -m hair_color_db.production.bootstrap
python3 -m unittest hair_color_db.production.test_pg_e2e -v
```

## PostgreSQL end-to-end wiring

| Module | Role |
|---|---|
| `db.py` | Central `DATABASE_URL` resolution, engine + session factory |
| `migrate.py` | Compatibility CLI that delegates schema upgrades to Alembic |
| `bootstrap.py` | Alembic upgrade + Stage 12 import + Stage 13 import (one command) |
| `catalog_lookup.py` | Resolve brand/line/region/shade UUIDs from imported catalog |
| `persist.py` | Write `persistence_payload` → `formula` / `formula_step` / `risk_assessment` |
| `run_production_engine.py` | CLI: run `SqlAlchemyEngineRepository` + optional persist |
| `shade_matching.py` | PostgreSQL shade search/ranking and reference lookup |
| `query_production_engine.py` | CLI: level/tone shade search against PostgreSQL |

Typical local workflow:

```bash
cp .env.example .env
docker compose up -d
export DATABASE_URL=postgresql+psycopg2://haircolor:haircolor@localhost:5432/haircolor
python3 -m hair_color_db.production.bootstrap
python3 -m hair_color_db.production.run_production_engine \
  --bootstrap \
  --canonical-key "Matrix::SoColor::US" \
  --shade-code 5NN \
  --gray-percentage 60 \
  --service-intent gray_coverage \
  --persist
```

Import CLIs (`import_stage12_research`, `import_stage13_rules`), `bootstrap.py`, and `migrate.py` all read
`DATABASE_URL` or accept `--database-url`.

### Shade search / matching (PostgreSQL)

Port of the Phase 1 SQLite `query_engine.py` / `src/matching.py` scoring against
imported research tables:

```bash
python3 -m hair_color_db.production.query_production_engine \
  --level 7 --tones Ash --brand "Wella"
```

Reference lookup (permanent line preference, brand/line hints):

```bash
python3 -m hair_color_db.production.run_production_engine \
  --shade-ref "Wella Professionals::Koleston Perfect::7/1" \
  --gray-percentage 30
```

`sub_range` / collection on the resolved shade record is applied automatically as
`selected_sub_ranges` for Stage 13 rules unless `--sub-range` overrides it.

Stage 12 import now populates `shade_tone_code` links so normalized tones resolve via
`shade → tone_code_reference → tone_normalization → normalized_tone`.

### Cross-engine validation (Stage C)

`test_cross_engine_validation.py` runs each case in `F_validation_cases.json` through:

1. Stage 13 `resolve_formulation_rules()`
2. Production `run_engine()` with equivalent `EngineInput` and `context_overrides`

Warning-only rule actions intentionally resolve to `caution` in both engines. The Stage 13
resolver and production `derive_recommendation_status()` therefore share the same status
semantics for validation cases while still comparing `matched_rules`, `developer_volume`,
and `block_reason`.
