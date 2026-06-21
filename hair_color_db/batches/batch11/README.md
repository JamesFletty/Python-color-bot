# Color Bot Normalized Extract v5 — Schwarzkopf IGORA ROYAL

Source: `445122692-schwarzkopf-quick-starter-guide(1).pdf`

## Contents

- `normalized_shades.csv` — 111 active shade / modifier records from the IGORA ROYAL assortment pages.
- `normalized_technical_rules.csv` — 22 normalized technical, developer, gray coverage, lift, mixtone, extract, pastel, Fashion Lights, and application rules.
- `formula_recreation_rules.csv` — 40 previous-shade recreation formulas from the mixing recommendations cheat sheet.
- `source_documents.csv` — source-document metadata for traceability.
- `normalized_haircolor_seed_package.json` — package summary and schema-alignment notes.

## Important modeling note

Do not flatten the page 6 mixing recommendations into active shade inventory. They are migration/recreation formulas for previous shades and should remain separate or be loaded as `formulation_rule` rows with a dedicated `package_rule_id`.

Modifiers such as `0-11`, `0-22`, `0-33`, boosters, `D-0`, `E-0`, and `E-1` are represented as `shade_category=modifier` because the current export shape does not expose a dedicated `tone_modifier` table.

## Source coverage

Pages 4–5: active assortment.
Page 6: previous shade recreation formulas.
Pages 7–10: numbering system, 360° assortment technical use, developer usage, application methods, mixing, development time, rinsing.
