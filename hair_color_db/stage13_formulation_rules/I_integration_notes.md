# Stage 13 Integration Notes

## Purpose

Stage 13 packages deterministic formulation rules as versioned JSON artifacts (sections A–I) that sit above Stage 12 research data and feed the production formula engine (`hair_color_db/production/`).

## Load order

1. **Stage 12** — `A_brand_line_inventory.json`, `C_normalized_shade_records.json`, `D_line_technical_records.json`
2. **Stage 13 ontology** — `A_formulation_ontology.json` (entities, enums, developer profiles, pigment map)
3. **Universal rules** — `B_universal_rule_library.json` (U001–U018)
4. **Line overrides** — `D_brand_line_overrides.json` via `active_override_groups()` in `loaders.py`
5. **Decision order** — `E_decision_order.json` defines evaluation phases
6. **Production engine** — `run_engine()` in `formula_builder.py`

## Line override activation

Matrix Coil Color, Super Sync, and Tonal Control shade inventory was added in Stage 12 batch05 (section C). Their line override groups in `D_brand_line_overrides.json` are active via `active_override_groups()` in `loaders.py`.

## Validation cases

`F_validation_cases.json` contains 20 validation cases (VC001, VC003–VC013, VC019, VC023–VC029). Run against the engine after importing rules to confirm:

- Safety gates (patch test)
- Gray blend vs full cover boundaries
- Direct dye / no-developer paths
- Intermixing blocks (HD, Sync)
- Pre-lightened-only lines (Tonal Control)
- Warning-only actions resolving to `caution` consistently in Stage 13 and production
- Deposit/fill and lift developer precedence rules (U013–U018)

## Schema extension

`H_schema_extension_proposal.json` proposes `service_workflow`, `validation_case`, and `formulation_rule_evidence` tables plus dormant-rule columns on `formulation_rule`. Import scripts should map package `rule_id` strings to UUID primary keys while retaining `package_rule_id` for traceability.

## Known gaps

See `G_conflicts_and_gaps.json` (G005) for remaining inventory and workflow coverage items.

## Regenerating artifacts

```bash
python3 hair_color_db/stage13_formulation_rules/emit_artifacts.py
```
