# Research vs Production Schema

## Assumptions

- The **research layer** (18 tables from `stage12_package/H_schema_proposal.json`) is deployed first with **UUID** primary keys on all canonical entities (`brand_id`, `line_id`, `shade_id`, etc.).
- Research ingest populates `shade_raw` (append-only), rebuilds `shade`, and loads `line_technical_rule` rows split from Stage 5 JSON.
- `sub_range` rows exist before shade uniqueness is enforced (`UNIQUE(line_region_id, sub_range_id, shade_code)`).
- Operational seeds that reference Matrix SoColor sub-ranges run only when matching research data is present; missing rows are skipped safely.
- **`client_id`**, **`stylist_id`**, **`salon_id`**, and **`formula_outcome.reported_by`** are external identity UUIDs stored in this database but **not FK-enforced**. They reference stylist/salon/client services that live outside the hair-color research schema. No `client`, `stylist`, or `salon` tables exist in this repo.
- **`pgcrypto`** is enabled (`CREATE EXTENSION IF NOT EXISTS pgcrypto`) so `gen_random_uuid()` defaults work on fresh PostgreSQL installs.

## Responsibilities

| Layer | Role | Mutability |
|---|---|---|
| **Research DB** | Source-traceable manufacturer facts: brands, lines, shades, tone maps, line technical rules, provenance | Append-only raw (`shade_raw`); normalized tables rebuilt deterministically from raw + mappings |
| **Production DB** | Same PostgreSQL database (or read replica) with **additive operational tables** for the deterministic formula engine and PRD workflow | Operational tables are transactional; research facts are read, not overwritten |

The production layer does **not** replace or redesign the research schema. It reads research facts and adds:

1. **Universal color science** — brand-agnostic lift/neutralization reference (levels 1–12).
2. **Typed facets on `line_technical_rule`** — queryable columns alongside preserved `rule_value` JSON.
3. **`shade_intermixing_rule`** — compact safety/compatibility rules (sub-range scoped where needed).
4. **`formulation_rule`** + **`formulation_rule_brand`** / **`formulation_rule_line`** — engine condition/action rules with join-table applicability (no UUID[] FK arrays).
5. **PRD domain tables** — `consultation`, `hair_profile`, `formula`, `formula_step`, `risk_assessment`, `formula_outcome`.

## Why the research layer stays append-only

Manufacturer extractions are evidence-bearing artifacts. Overwriting raw wording would destroy auditability and make re-normalization non-reproducible. The research pipeline therefore:

- Appends new `shade_raw` rows per `ingestion_run`.
- Versions changes through `record_version`.
- Stores conflicts as additional `record_source` rows plus `issue_log` entries.

The formula engine **reads** normalized `shade` rows and `line_technical_rule` facts; it never writes back to research tables during a consultation.

## How data feeds the deterministic engine

```mermaid
flowchart LR
    subgraph Research
        SR[shade_raw]
        SH[shade]
        LTR[line_technical_rule]
        TN[tone_normalization]
        SD[source_document]
        PL[product_line]
    end
    subgraph Production
        UCS[universal_color_science]
        SIR[shade_intermixing_rule]
        FR[formulation_rule]
        HP[hair_profile]
        FM[formula]
    end
    SR --> SH
    LTR --> Engine
    TN --> Engine
    SH --> Engine
    UCS --> Engine
    SIR --> Engine
    FR --> Engine
    HP --> Engine
    Engine --> FM
    FM -->|line_id| PL
    SD -. provenance .-> LTR
    SD -. provenance .-> SIR
    SD -. provenance .-> FR
```

1. **`hair_profile`** captures consultation intake (levels, porosity, gray %, chemical history).
2. **`universal_color_science`** supplies underlying pigment and neutralizing tone by level for lift/neutralization math.
3. **`line_technical_rule`** provides line/sub-range defaults (developer volume, mixing ratio, processing time, gray coverage); typed columns are preferred when populated, with JSON fallback.
4. **`shade_intermixing_rule`** filters invalid shade/sub-range combinations before steps are assembled.
5. **`formulation_rule`** applies prioritized condition/action JSON (developer adjustments, workflows, risk modifiers) scoped by brand/line join tables.
6. Output is persisted as **`formula`** + **`formula_step`** + **`risk_assessment`**; post-service feedback goes to **`formula_outcome`**.

## Formula brand / line modeling (final decision)

**`formula` stores only `line_id`, not `brand_id`.**

Brand is always derived at read time:

```sql
SELECT f.*, pl.brand_id
FROM formula f
JOIN product_line pl ON pl.line_id = f.line_id;
```

This prevents a formula from referencing a `line_id` that belongs to a different brand than a separately stored `brand_id` — a drift scenario that CHECK constraints cannot solve without duplicating `product_line.brand_id` into `formula`.

## UUID generation (final decision)

Primary keys use **`gen_random_uuid()`** as PostgreSQL column defaults for operational tables, plus explicit `gen_random_uuid()` in seed `INSERT … SELECT` statements.

**Requirement:** run `CREATE EXTENSION IF NOT EXISTS pgcrypto` before applying DDL or the Alembic migration. This is included at the top of both `production_operational_schema.sql` and `alembic_revision.py`.

ORM inserts use `default=uuid.uuid4` when the application supplies IDs; DB defaults apply for raw SQL seeds.

## Applicability semantics (`formulation_rule`)

| `formulation_rule_brand` | `formulation_rule_line` | Meaning |
|---|---|---|
| empty | empty | Universal rule |
| rows present | empty | All lines for listed brands |
| rows present | rows present | Only listed lines (lines must belong to scoped brands in application logic) |

Brand/line scope uses **join tables**, not PostgreSQL UUID arrays, so FK integrity and index-friendly filtering are preserved.

## Intermixing rule scopes (`shade_intermixing_rule`)

| `rule_scope` | Meaning |
|---|---|
| `sub_range_isolated_from_line` | Shades in `applies_to_sub_range_id` cannot mix with any other sub-range in the line (HD, Ultra Blonde) |
| `sub_range_internal_only` | Mixing allowed only within the same sub-range (SoColor 10 min) |
| `cross_sub_range` | Pairwise or caution between sub-ranges (Extra Coverage + Blended/Reflect; DreamAge vs non-DreamAge) |
| `shade_pair` | Explicit shade-level exception |

## `universal_color_science.neutralizing_tone_id`

After seeding levels 1–12, a migration step links `neutralizing_tone_id` **only when** `neutralizing_tone` matches a single `normalized_tone.tone_name` exactly:

| Level | `neutralizing_tone` seed | Linked? | Reason |
|---|---|---|---|
| 5 | `Green` | Yes → `Green` | Exact taxonomy match |
| 6 | `Blue` | Yes → `Blue` | Exact taxonomy match |
| 9 | `Violet` | Yes → `Violet` | Exact taxonomy match |
| 1–4, 7–8, 10 | `Blue/Violet`, `Green/Blue`, `Violet/Ash` | No (NULL) | Compound labels; mapping to one `normalized_tone` row would be unsafe |
| 11–12 | NULL | No (NULL) | High-lift categories; no pigment fields seeded |

The free-text `neutralizing_tone` column is retained for display and educator reference even when `neutralizing_tone_id` is NULL.

## Deviations from the original spec

| Topic | Original request | Final implementation | Why |
|---|---|---|---|
| Brand/line applicability | UUID[] FK arrays | `formulation_rule_brand` + `formulation_rule_line` join tables | PostgreSQL cannot enforce UUID[] FK arrays |
| `formula.brand_id` | Both `brand_id` and `line_id` on formula | **`brand_id` removed**; brand derived via `line_id → product_line.brand_id` | Prevents line/brand drift; simplest safe design |
| `shade_intermixing_rule` modeling | Pair-only rows | `rule_scope` enum + `line_region_id` | Avoids thousands of shade-pair seeds |
| `consultation` identity FKs | UUID FK | UUID columns **without FK** | External stylist/salon/client services out of scope |
| `confidence` on `universal_color_science` | ENUM name `confidence` | PostgreSQL type `color_science_confidence` | Avoids collision with research `source_confidence` |
| Intermixing seed `source_id` | NOT NULL FK | Title lookup (`%2023 Matrix Manual%`) | Links to existing catalog row when research DB is loaded |
| `line_technical_rule.developer_volume` | Narrow whitelist (10/20/30/40) | `> 0 AND <= 100` | Supports volume convention without over-restricting typed backfill |
| `line_technical_rule` mixing ratio | Independent nullable columns | **Pair CHECK**: both NULL or both positive | Prevents half-populated ratios |
| UUID defaults | `gen_random_uuid()` without extension note | **`pgcrypto` extension required** and enabled in DDL/migration | Fresh installs otherwise fail |
| `neutralizing_tone_id` seeds | Populate when possible | Exact `tone_name` match only (levels 5, 6, 9) | Compound tone strings are ambiguous |
| Pydantic `formulation_rule` | `dict[str, Any]` for condition/action | **`RuleCondition` / `RuleAction`** typed models | Strong API validation; still stored as JSONB |

## File layout

```
hair_color_db/production/
  production_operational_schema.sql   # Standalone DDL + seeds
  production_models.py                # SQLAlchemy 2.0 ORM
  production_schemas.py               # Pydantic v2 Create/Update/Response
  alembic_revision.py                 # Migration (upgrade + downgrade + backfill)
  research_vs_production_schema.md    # This document
```

## Applying the migration

1. Deploy research baseline DDL (from `H_schema_proposal.json` — separate migration `research_baseline`).
2. Ensure `pgcrypto` is available (included in operational DDL/migration).
3. Copy `alembic_revision.py` into your Alembic versions directory or run `production_operational_schema.sql` directly.
4. Re-run research ingest after mapping changes; operational seeds for Matrix intermixing rules require `sub_range` names matching ingest (`HD`, `Ultra Blonde`, `Extra Coverage`, `Blended`, `Reflect`, `DreamAge`, `SoColor 10 min`).

## `line_technical_rule` backfill (recognized JSON)

The Alembic revision backfills typed columns only when `rule_value` matches deterministic shapes documented in `alembic_revision.py` module docstring (`developer`, `mixing_ratio`, `processing_time`, `gray_coverage`, `lift`). Unparseable or ambiguous JSON is skipped without failing the migration. **`rule_value` is never modified.**
