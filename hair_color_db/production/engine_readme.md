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
| `test_import_stage13_rules.py` | Stage 13 import pipeline regression tests |

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

## Assumptions

- `formula` stores `line_id` only; brand derived at read time.
- Shade selection is supplied on input (`selected_shades`); the engine does not search the shade catalog.
- Quantity grams are placeholders (60g default) until a future gram-age module exists.
- Research tables are read-only through repositories.

## Known limitations

- No SQL persistence write in `run_engine()` — returns `persistence_payload` for caller to commit.
- Single primary line per recommendation (no multi-line formulas).
- `developer_override` intermixing rules are modeled but not yet applied to developer selection.
- JSON `rule_value` fallback parsing is intentionally narrow (developer volume, mixing ratio string).

## Running tests

```bash
pip install pydantic sqlalchemy
python3 -m unittest hair_color_db.production.test_engine -v
```
