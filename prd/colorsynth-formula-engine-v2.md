# ColorSynth Formula Engine — v2 Architecture, PRD & Implementation Plan

**Author:** JamesFletty  
**Date:** 2026-06-22  
**Status:** Draft — Ready for Review  
**Scope:** Rebuild the hair-color formula engine to preserve all stylist-level domain logic while eliminating infrastructure bloat, dead code, and premature abstraction.

> **Repo-verified inventory (2026-06-22):** Stage12 contains **2,537** shades (not 2,456),
> **1,032** cross-line entries, and **143** formulation rules (18 universal + 125 line overrides
> across 18 brand/line groups). Tone mapping count is **1,022** per `src/paths.py`.

---

## 1. Executive Summary

The current codebase (418 files, ~21 MB) supports the full domain surface required for professional hair-color formulation: multi-brand shade catalogs (2,456 shades / 950 tone mappings across 10+ brands), cross-line translation, gray-coverage rules, elasticity-aware rule matching, and a natural-language parsing layer. The core domain knowledge is solid. The infrastructure carrying it is not.

The v1 codebase has accumulated three distinct problems that compound each other:

**Layering rot.** The same formula logic lives in three separate places: `src/` (SQLite-native), `hair_color_db/production/` (PostgreSQL-native), and `api/formula_dispatch.py` (runtime switch between them). Every behavioral change has to be made twice or it silently diverges.

**Data fragmentation.** The canonical shade data is split across `hair_color_db/batches/` (11 batches of per-batch JSON), `hair_color_db/stage12_package/` (a consolidated 6.5 MB snapshot), `hair_color_db/reference/` (brand-specific CSVs and JSON), and a separate `hair-color-db/` directory at the repo root containing a lone orphaned JSON file. The stage12 snapshot (`C_normalized_shade_records.json`) is 4.3 MB. These all track to the same underlying shade inventory — they just represent it in three different forms at different points in a pipeline that no longer runs incrementally.

**Provider sprawl.** The `.env.example` documents four LLM providers (Azure OpenAI, direct OpenAI, xAI Grok, and AWS Bedrock via the OpenAI-compatible Mantle endpoint) plus an offline mock. `ai_service.py` imports and instantiates `AsyncAzureOpenAI` and `AsyncOpenAI` from the `openai` SDK. `requirements.txt` lists `boto3`, `botocore`, `httpx-aws-auth`, and `openai` simultaneously. The Bedrock configuration in `.env.example` uses the Mantle OpenAI-compatible endpoint rather than native `boto3`/Converse API — meaning the existing "Bedrock" integration is actually running through the OpenAI SDK with a custom base URL, not through boto3 at all.

**v2 Goal:** Consolidate to a single data store, a single engine implementation, and a single LLM provider while retaining every piece of domain intelligence the v1 system accumulated.

See [`README-v2.md`](../README-v2.md) for branch status and Phase 1 commands.

---

## 2. Current-State Inventory (Repo-Verified)

| Metric | v1 Actual |
|--------|-----------|
| Total files (excl. node_modules/git) | 418 |
| JSON files in repo | 141 |
| Python source files | 119 |
| `hair_color_db/` total size | 21 MB |
| `hair_color_db/batches/` | 12 MB across 11 batches |
| `hair_color_db/stage12_package/` | 6.5 MB (consolidated snapshot) |
| Shade inventory (authoritative) | 2,537 shades, 1,022 tone mappings |
| LLM providers in `.env.example` | 4 (Azure, OpenAI, xAI, Bedrock-Mantle) |
| Formula engine implementations | 2 (`src/`, `hair_color_db/production/`) |
| Frontend directories | 2 (`frontend/`, `artifacts/mockup-sandbox/`) |
| `production_models.py` alone | 1,039 lines |
| `alembic_revision.py` alone | 1,188 lines |

### What's Actually Load-Bearing

These are the files that contain real, hard-won domain knowledge that v2 must preserve:

- `hair_color_db/stage12_package/C_normalized_shade_records.json` — canonical shade inventory
- `hair_color_db/stage12_package/J_cross_line_conversion_map.json` — cross-line mappings
- `hair_color_db/stage13_formulation_rules/B_universal_rule_library.json` — universal formulation rules
- `hair_color_db/stage13_formulation_rules/D_brand_line_overrides.json` — per-brand/line rule overrides
- `hair_color_db/reference/` — brand-specific CSVs (Aveda, Redken, Schwarzkopf, Pravana, etc.)
- `api/formula_text_parser.py` — natural-language shade parsing
- `hair_color_db/production/shade_matching.py` — level + tone ranking logic
- `hair_color_db/production/rule_evaluator.py` — gray/porosity/elasticity rule matching
- `hair_color_db/production/fill_shade_lookup.py` — fill pigment computation
- `hair_color_db/production/safety_checks.py` — contraindication rules

### What Can Be Deleted (Phase 5)

- `hair_color_db/batches/` — superseded by stage12_package
- `hair-color-db/` (root) — orphaned JSON
- `hair_color_db/stage01_discovery/` through `stage11_gaps/`
- `hair_color_db/sources/`, `hair_color_db/tools/`
- `src/` — SQLite-only layer
- `artifacts/mockup-sandbox/`
- `static/dist/`
- `api/ai_mock.py`
- Multi-tenant consultation scaffolding (no active users)
- `.agents/memory/`

---

## 3. v2 Architecture

### 3.1 Stack

| Layer | v2 Choice | Rationale |
|-------|-----------|-----------|
| **Runtime** | Python 3.12 + FastAPI | Keep what works |
| **Database** | PostgreSQL 16 | Single source of truth |
| **ORM** | SQLAlchemy 2.0 + Alembic | Drop SQLite/ENGINE_BACKEND switch |
| **LLM** | OpenAI SDK + Bedrock Mantle endpoint | One code path, env-var endpoint swap |
| **Frontend** | React 18 + Vite + shadcn/ui (selective) | One SPA |
| **Deploy** | Docker + Docker Compose | ECS/Fargate ready |
| **CI/CD** | GitHub Actions (one workflow) | Simplify |

### 3.2 Repository Layout

```
├── app/                    # FastAPI + engine (v2)
├── data/seed/              # CSV seed artifacts (no JSON in git long-term)
├── scripts/                # export + seed + audit
├── tests/v2/               # v2 test suite
├── frontend/               # React SPA (cleaned Phase 4)
├── alembic/                # Fresh v2 migrations (Phase 2)
├── pyproject.toml
└── README-v2.md
```

**Target:** ~50 source files (excluding tests and seed data).

---

## 4. Data Model

Core tables: `brands`, `product_lines`, `shades`, `shade_tones`, `formulation_rules`, `cross_line_mappings`, plus a stub `consultations` table (no API surface yet).

Formulation rules retain JSON `rule_condition` / `rule_action` columns (same evaluation surface as v1 production import) rather than a lossy flatten — confirmed during Phase 1 export.

---

## 5–12. API, LLM, Engine, Frontend, Migration, Acceptance, Risks, File Mapping

Full specification unchanged from original draft. Key migration phases:

| Phase | Scope | Status on this branch |
|-------|-------|----------------------|
| **1** | Data export + validation | **Complete** |
| **2** | Alembic schema + engine port | Pending |
| **3** | API routers + LLM client | Pending |
| **4** | Frontend cleanup | Pending |
| **5** | v1 deletion + deploy | Pending |

### Phase 1 deliverables (this branch)

- `scripts/audit_stage_data.py` — inventory audit
- `scripts/export_stage12_to_csv.py` — shades + brands/lines
- `scripts/export_stage13_to_csv.py` — formulation rules (JSON preserved)
- `scripts/export_crossline_to_csv.py` — cross-line mappings
- `data/seed/*.csv` — generated seed artifacts
- `tests/v2/test_export_validation.py` — parity checks
- `app/` scaffold — config + health endpoint

---

*End of Document*
