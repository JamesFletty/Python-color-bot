"""Product-line mappings for normalized seed package → Stage 12 conversion."""

from __future__ import annotations

LINE_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("Aveda", "Full Spectrum Permanent Hair Color"): {
        "canonical_key": "Aveda::Full Spectrum Permanent::US",
        "product_line": "Full Spectrum Permanent",
        "color_type": "permanent",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Core"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Core",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Highlifts"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Highlifts",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Fashion Lights"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Fashion Lights",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Absolutes"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Absolutes",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Specialties"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Specialties",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Pastels"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Pastels",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Creative Mixtones"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "additive",
        "sub_range": "Creative Mixtones",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Extracts"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "additive",
        "sub_range": "Extracts",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
    },
    ("Redken", "Shades EQ Gloss / Bonder Inside"): {
        "canonical_key": "Redken::Shades EQ Gloss::US",
        "product_line": "Shades EQ Gloss",
        "color_type": "demi",
    },
    ("Redken", "Color Gels Lacquers"): {
        "canonical_key": "Redken::Color Gels Lacquers::US",
        "product_line": "Color Gels Lacquers",
        "color_type": "permanent",
    },
    ("Redken", "Color Fusion Advanced Performance Color Cream"): {
        "canonical_key": "Redken::Color Fusion::US",
        "product_line": "Color Fusion",
        "color_type": "permanent",
    },
    ("Redken", "Cover Fusion Low Ammonia Color Cream"): {
        "canonical_key": "Redken::Cover Fusion::US",
        "product_line": "Cover Fusion",
        "color_type": "permanent",
    },
    ("Redken", "Color Gels Oils"): {
        "canonical_key": "Redken::Color Gels Oils::US",
        "product_line": "Color Gels Oils",
        "color_type": "permanent",
    },
    ("Redken", "Color Gels 10 Minute"): {
        "canonical_key": "Redken::Color Gels 10 Minute::US",
        "product_line": "Color Gels 10 Minute",
        "color_type": "permanent",
    },
    ("Moroccanoil", "Color Rhapsody Permanent / Color Calypso Demi-Permanent"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
    },
    ("Moroccanoil", "Color Rhapsody Ultimates Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "Ultimates",
    },
    ("Moroccanoil", "Color Rhapsody High Lift"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "High Lift",
    },
    ("Moroccanoil", "Color Calypso / Color Rhapsody shared"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
    },
    ("Moroccanoil", "Color Infusion Pure Color Mixer"): {
        "canonical_key": "Moroccanoil Professional::Color Infusion::US",
        "product_line": "Color Infusion",
        "color_type": "additive",
    },
    ("Wella Professionals", "Koleston Perfect ME+"): {
        "canonical_key": "Wella Professionals::Koleston Perfect::US",
        "product_line": "Koleston Perfect",
        "color_type": "permanent",
    },
    ("Wella Professionals", "Color Touch"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "demi",
    },
    ("Wella Professionals", "Color Touch Plus"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "demi",
        "sub_range": "Plus",
    },
    ("Wella Professionals", "Color Touch Sunlights"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "demi",
        "sub_range": "Sunlights",
    },
    ("Wella Professionals", "Color Touch Relights"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "demi",
        "sub_range": "Relights",
    },
    ("Wella Professionals", "Color Touch Special Mix"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "additive",
        "sub_range": "Special Mix",
    },
    ("Wella Professionals", "Color Touch Instamatic"): {
        "canonical_key": "Wella Professionals::Color Touch::US",
        "product_line": "Color Touch",
        "color_type": "demi",
        "sub_range": "Instamatic",
    },
    ("Matrix", "SoColor Pre-Bonded"): {
        "canonical_key": "Matrix::SoColor::US",
        "product_line": "SoColor",
        "color_type": "permanent",
        "sub_range": "Pre-Bonded",
    },
    ("Matrix", "SoColor Sync Pre-Bonded"): {
        "canonical_key": "Matrix::SoColor Sync::US",
        "product_line": "SoColor Sync",
        "color_type": "demi",
        "sub_range": "Pre-Bonded",
    },
    ("Matrix", "Coil Color"): {
        "canonical_key": "Matrix::Coil Color::US",
        "product_line": "Coil Color",
        "color_type": "permanent",
    },
    ("L'Oréal Professionnel", "Dia Light"): {
        "canonical_key": "L'Oréal Professionnel::Dia Light::US",
        "product_line": "Dia Light",
        "color_type": "demi",
    },
    ("L'Oréal Professionnel", "Dia Richesse"): {
        "canonical_key": "L'Oréal Professionnel::Dia Richesse::global",
        "product_line": "Dia Richesse",
        "color_type": "demi",
    },
}

TECH_LINE_MAP: dict[tuple[str, str | None], dict[str, str]] = {
    **{(brand, line): cfg for (brand, line), cfg in LINE_MAP.items()},
    ("Moroccanoil", "Color Calypso Demi-Permanent Gloss"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
        "sub_range": "Gloss",
    },
    ("Moroccanoil", "Color Calypso Demi-Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Calypso::US",
        "product_line": "Color Calypso",
        "color_type": "demi",
        "sub_range": "Cream",
    },
    ("Moroccanoil", "Color Rhapsody High Lift Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
        "sub_range": "High Lift",
    },
    ("Moroccanoil", "Color Rhapsody Permanent Cream Color"): {
        "canonical_key": "Moroccanoil Professional::Color Rhapsody::US",
        "product_line": "Color Rhapsody",
        "color_type": "permanent",
    },
    ("Redken", "Color Fusion Extra Lift"): {
        "canonical_key": "Redken::Color Fusion::US",
        "product_line": "Color Fusion",
        "color_type": "permanent",
        "sub_range": "Extra Lift",
    },
    ("Matrix", None): {
        "canonical_key": "Matrix::SoColor::US",
        "product_line": "SoColor",
        "color_type": "permanent",
    },
    ("Matrix", "Tonal Control Pre-Bonded"): {
        "canonical_key": "Matrix::Tonal Control::US",
        "product_line": "Tonal Control",
        "color_type": "demi",
        "sub_range": "Pre-Bonded",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Pastels"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "permanent",
        "sub_range": "Pastels",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Creative Mixtones"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "additive",
        "sub_range": "Creative Mixtones",
    },
    ("Schwarzkopf Professional", "IGORA ROYAL Extracts"): {
        "canonical_key": "Schwarzkopf Professional::IGORA ROYAL::US",
        "product_line": "IGORA ROYAL",
        "color_type": "additive",
        "sub_range": "Extracts",
    },
}

BATCH10_BRANDS = frozenset({"Wella Professionals", "Matrix", "L'Oréal Professionnel"})

BATCH10_LINE_KEYS = frozenset(
    key for key in LINE_MAP if key[0] in BATCH10_BRANDS
)
