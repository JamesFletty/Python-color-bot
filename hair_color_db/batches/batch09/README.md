# Color Bot Normalized Extract — v3 Aveda Full Spectrum Expansion

This package updates the prior normalized extract with a fuller Aveda Full Spectrum Permanent Hair Color model.

## Aveda additions

- Natural Series base shades: `1Natural` through `10Natural`.
- Base components: `Intense Base`, `Extra Lifting Creme`, `Universal ØN`.
- Light Pure Tones:
  - `Light N/N`, `Light V/B`, `Light B/B`, `Light Y/O`, `Light O/R`.
- Dark Pure Tones:
  - `Dark N/N`, `Dark B/V`, `Dark B/G`, `Dark Y/O`, `Dark R/O`, `Dark V/R`.
- Precoloration-chart alias modifiers marked `parsed_review_required`:
  - `Dark R/R`, `Dark R/V`.
- Pure Pigments:
  - `Blue`, `Green`, `Yellow`, `Orange`, `Violet`, `Red`.
- Pastel Tones:
  - `Pastel Violet`, `Pastel Blue`, `Pastel Y/O`.
- Natural Series and Intense Series customized formula targets by level/family.
- Extra Lift Pastel Blonde standard formula targets.

## Aveda rules added

- `aveda_pure_tone_standard_amount_by_desired_level`
- `aveda_light_vs_dark_pure_tone_selection_by_level`
- `aveda_natural_series_customization_matrix`
- `aveda_intense_series_customization_matrix`
- `aveda_pure_pigment_usage_rules`
- `aveda_vibrancy_guide`
- `aveda_universal_on_customization_guide`
- `aveda_extra_lift_pastel_blonde_intensity_guide`
- `aveda_color_balancing_guide`
- `aveda_precoloration_target_level_formula_matrix`

## Schema note

Your current repository schema does not appear to have a dedicated `tone_modifier` table in the production layer, so modifiers are represented in `normalized_shades.csv` using `shade_category` values such as `tone_modifier`, `pure_pigment`, `pastel_tone_modifier`, and `base_component`.

That is compatible with current CSV/JSON seed ingestion, but the cleaner long-term schema would split these into:
- `shade`
- `base_component`
- `tone_modifier`
- `formula_component_rule`

## Source

Primary source: `452808418-Full-Spectrum-Color.pdf`, page 2 customization chart and page 1 formulation guidelines.
