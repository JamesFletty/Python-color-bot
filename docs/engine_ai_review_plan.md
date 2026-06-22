# Formula Engine + AI Prompt Review Plan

## Findings from the reported examples

1. **AI explanations are too authoritative about weak output.** The explanation layer can say the formula is correct even when the deterministic payload has assumptions, grounding substitutions, missing processing time, or no gray-coverage guidance. This makes bad picks look intentional.
2. **Natural-language goal parsing is under-weighted.** Requests such as “natural level 6, 50% grey, wants level 8 strawberry blonde” must preserve both the starting level and the target tone. The current grounding path has target-level support, but the prompt and deterministic text parser need stronger tone synonyms so “strawberry blonde” resolves to copper/red rather than a lazy natural shade.
3. **Free-text tone inference misses common salon phrases.** The deterministic parser primarily reads weighted formula components. When a user writes a goal instead of a formula, terms such as “red violet,” “strawberry blonde,” “intense red violet,” and “beige blonde” need to become explicit tone families before catalog ranking.
4. **Grounding notes are useful but not surfaced as quality gates.** The system can replace invalid LLM codes with catalog-backed options, but the user-facing copy should disclose substitutions and avoid presenting them as exact manufacturer formulas.
5. **Translation prompts are too loose for component preservation.** Translation must require source-component accounting, catalog-only target shades, preserved warmth/coolness, and a clear uncertainty flag when no direct equivalent exists.
6. **Formula output needs deterministic auditability.** Development should add visible rule coverage: selected shade source, matched Stage 13 rules, developer source, processing-time source, gray rule source, and data gaps.

## Fix plan

### Phase 1 — Immediate quality hardening

- Expand deterministic free-text tone inference for goal phrases: strawberry blonde, red-violet, copper-red, beige blonde, ash brown, neutral brown, and gray/grey coverage language.
- Treat “intense” as a sub-range/tone-strength hint, not a substitute for a real catalog shade.
- Strengthen formula parsing prompt to require: extract first-class inputs only, prefer target level over natural level for shade selection, preserve gray percentage, and never invent shade codes.
- Strengthen explanation prompt to summarize deterministic output only and disclose assumptions, warnings, grounding substitutions, and missing fields.
- Strengthen translation prompt to map every source component with grams, preserve warm/cool direction, choose target catalog shade only, and explicitly state when a direct equivalent was unavailable.

### Phase 2 — Engine diagnostics and tests

- Add regression tests for: level 6 / 50% gray / level 8 strawberry blonde; level 3 / 20% gray / level 5 intense red violet; Aveda booster formulas with Y/O, R/O, and B/G; and invalid LLM shade grounding.
- Add a response-level `quality_flags` block summarizing missing processing time, missing gray rule, fallback shade used, low-confidence catalog match, and blocked/caution Stage 13 statuses.
- Surface rule provenance in the UI in a compact “why this formula” panel rather than burying it in raw JSON.

### Phase 3 — Productization

- Build a curated synonym table per brand/line for manufacturer tone families and sub-ranges.
- Add cross-line conversion coverage metrics and fixture-based expected translations.
- Add a professional review workflow: formula can be marked “verified,” “needs correction,” or “unsafe/blocked,” producing fixtures for future regression tests.
