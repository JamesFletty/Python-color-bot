# Professional Hair Color Database — Acquisition & Normalization

Source-traceable, machine-readable dataset of professional salon hair color systems,
built for formula generation, formula conversion, and multi-brand mapping.

## Current coverage (v0.2, 2026-06-12)

| Layer | Count |
|---|---|
| Brands inventoried (Stage 1) | 20 seed brands, 133 product lines |
| Sources cataloged (Stage 2) | 152 (Tier 1 official prioritized) |
| Lines with shade-level extraction (Stages 4–9) | 10 lines / 5 brands |
| Normalized shade records | 1,112 |
| Manufacturer tone reference rows | 356 |
| Tone normalization mappings | 353 (8 codes explicitly unresolved) |

Extracted batches:

- **Batch 1** — Redken (Shades EQ Gloss, Color Gels Lacquers), Wella Professionals
  (Koleston Perfect, Color Touch), Schwarzkopf Professional (IGORA ROYAL, IGORA VIBRANCE)
- **Batch 2** — Matrix (SoColor, SoColor Sync), L'Oréal Professionnel (Majirel, Dia Light)

The remaining 127 inventoried lines are queued with explicit gap records
(`stage11_gaps/gap_risk_report.json`).

## Layout

```
hair_color_db/
  stage01_discovery/        Stage 1: brand & line inventory (+ per-group research files)
  stage02_sources/          Stage 2: source catalog & missing-source targets
  stage03_extraction_plan/  Stage 3: per-line extraction plan, batch definitions, blockers
  batches/batch01, batch02/ Stages 4–9 per batch:
      *_raw_shade_records.json        raw manufacturer wording (append-only layer)
      *_line_technical_records.json   line-wide rules, developer tables, tone legends
      tone_reference_stage6.json      decoded manufacturer tone notation
      tone_normalization_map_stage7.json  auditable mapping to normalized taxonomy
      normalized_shade_records_stage8.json  merged, database-ingestible records
      qa_findings_stage9.json         integrity checks
  stage10_schema/           Stage 10: relational schema proposal
  stage11_gaps/             Stage 11: gap / risk / licensing report
  stage12_package/          Stage 12: final package, sections A–I + MANIFEST.json
  tools/                    deterministic build scripts (Stages 6–9 per batch)
```

## Evidence model

Every meaningful record carries `source_url`, `source_document`,
`source_confidence` (`high|medium|low|unresolved`) and `evidence_status`
(`confirmed|partially_confirmed|inferred|conflicting|missing|unresolved`).
Inferred tone decodings are flagged (`ambiguity_flag`, `notes_on_ambiguity`)
and never silently merged with legend-confirmed meanings. Source conflicts are
preserved verbatim in the raw extraction files and surfaced in section G of the
final package.

## Normalized tone taxonomy

`Natural, Neutral, Ash, Blue, Green, Violet, Pearl, Gold, Beige, Copper, Red,
Mahogany, Mocha, Brown, Warm, Cool, Other` — manufacturer codes map many-to-many
onto this set with per-mapping rationale.

## Rebuilding normalized layers

```bash
python3 hair_color_db/tools/build_stages_6_to_9_batch01.py
python3 hair_color_db/tools/build_stages_6_to_9_batch02.py
```

Both scripts are pure functions of the committed Stage 4–5 raw files.

## Licensing note

Extracted facts (codes, levels, ratios) are stored with provenance; manufacturer
chart PDFs and swatch imagery are **not** redistributed. See
`stage12_package/I_gap_risk_licensing_report.json` before any commercial use.
