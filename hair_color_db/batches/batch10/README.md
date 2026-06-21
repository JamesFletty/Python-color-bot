# Color Bot Normalized Extract v4 — Wella / Matrix / L'Oréal Expansion

This package extends the v3 Aveda Full System seed package with five additional uploaded sources:

- Wella Professionals Koleston Perfect ME+ colour chart
- Wella Professionals Color Essential notes
- Wella Professionals Color Touch Rob Eaton 2020 eBook
- Matrix 2023 Haircolor Manual
- L'Oréal Professionnel Dia Light / Dia Richesse color chart

## Output files

- `normalized_haircolor_seed_package.json`
- `normalized_shades.csv`
- `normalized_technical_rules.csv`
- `source_documents.csv`

## Scope added in v4

### Wella Koleston Perfect ME+
Extracted Pure Naturals, Rich Naturals, Deep Browns, Vibrant Reds, Special Blondes, and Special Mix shade records. Added rules for white-hair Pure Naturals additions, standard and Special Blonde processing, numbering/tone system, and lightening/underlying pigment logic.

### Wella Color Touch
Extracted Color Touch Plus, Sunlights, Relights, Special Mix, and Instamatic records. Added rules for Color Touch emulsion, Plus 4% requirement, Special Mix intensity formulas, Relights touch-of-gloss, Instamatic processing, dilution, and neutralization examples.

### Matrix
Extracted selected SoColor, Coil Color, SoColor Sync, modifier, and toner records from machine-readable chart areas. Added rules for Hair Diversity Matrix underlying pigments, developer lift, SoColor processing, refresh restrictions, lift by palette, Coil Color, SoColor Sync, Tonal Control, and Clear/Totally Transparent dilution.

### L'Oréal Professionnel Dia
Extracted Dia Light and Dia Richesse shade records from the chart pages where recoverable. Added rules for Diactivateur preparation, Dia Richesse coverage/lift, Dia Light acidic zero-lift behavior, and color-refreshing technique.

## Quality flags

Records with clean table rows or explicit source statements are marked `confirmed`.
Records recovered from dense chart/OCR layouts where names or subrange placement may need manual review are marked `parsed_review_required`.

This avoids silently overstating messy PDF extraction as production-perfect data.
