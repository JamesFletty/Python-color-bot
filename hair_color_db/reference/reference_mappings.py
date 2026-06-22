"""Shared mappings for reference pack import."""

from __future__ import annotations

# Display line name → Stage 12 canonical_key
LINE_CANONICAL: dict[str, str] = {
    "Shades EQ Gloss": "Redken::Shades EQ Gloss::US",
    "Color Gels Lacquers": "Redken::Color Gels Lacquers::US",
    "Color Gels 10 Minute": "Redken::Color Gels 10 Minute::US",
    "Full Spectrum Permanent": "Aveda::Full Spectrum Permanent::US",
    "Majirel": "L'Oréal Professionnel::Majirel::US",
    "Dia Light": "L'Oréal Professionnel::Dia Light::US",
    "Dia Richesse": "L'Oréal Professionnel::Dia Richesse::US",
    "IGORA VIBRANCE": "Schwarzkopf Professional::IGORA VIBRANCE::US",
    "IGORA ROYAL Core": "Schwarzkopf Professional::IGORA ROYAL::US",
    "Color Rhapsody Permanent Cream Color": "Moroccanoil Professional::Color Rhapsody::US",
    "SoColor Pre-Bonded": "Matrix::SoColor Pre-Bonded::US",
    "SoColor": "Matrix::SoColor::US",
    "Color Insider": "Matrix::Color Insider::US",
    "Koleston Perfect": "Wella Professionals::Koleston Perfect::US",
    # Pravana ChromaSilk lines
    "ChromaSilk Creme": "Pravana::ChromaSilk Creme Color::US",
    "ChromaSilk Creme Color": "Pravana::ChromaSilk Creme Color::US",
    "Express Tones": "Pravana::ChromaSilk Express Tones::US",
    "Ultra Hi-Lifts": "Pravana::ChromaSilk Ultra Hi-Lifts::US",
    "Correctors/Additives": "Pravana::ChromaSilk Correctors::US",
}

# Brand conversion chart source lines → Stage 12 canonical_key
BRAND_CONVERSION_SOURCE: dict[str, str] = {
    "Goldwell Topchic": "Goldwell::Topchic::US",
    "Matrix Color Insider": "Matrix::Color Insider::US",
    "Matrix SoColor": "Matrix::SoColor::US",
}

PRAVANA_CHROMASILK_TARGET = "Pravana::ChromaSilk Creme Color::US"
SEQ_CK = LINE_CANONICAL["Shades EQ Gloss"]
VIBRANCE_CK = LINE_CANONICAL["IGORA VIBRANCE"]
MATRIX_INSIDER_CK = LINE_CANONICAL["Color Insider"]

MATRIX_INSIDER_SUFFIX_TO_TONES: dict[str, list[str]] = {
    "N": ["Natural"],
    "A": ["Ash"],
    "AA": ["Ash", "Blue"],
    "V": ["Violet"],
    "G": ["Gold"],
    "GC": ["Gold", "Copper"],
    "GV": ["Gold", "Violet"],
    "C": ["Copper"],
    "M": ["Mahogany", "Red"],
    "R": ["Red"],
    "RC": ["Red", "Copper"],
    "RV": ["Red", "Violet"],
    "RR+": ["Red"],
    "BR": ["Brown", "Red"],
    "BC": ["Blue", "Copper"],
    "WM": ["Warm", "Mahogany"],
    "NW": ["Natural", "Warm"],
}

# Manufacturer tone family labels → normalized tone vocabulary
TONE_FAMILY_TO_NORMALIZED: dict[str, list[str]] = {
    "Pearl": ["Pearl"],
    "Gold": ["Gold"],
    "Gold Iridescent": ["Gold"],
    "Warm Gold": ["Gold", "Warm"],
    "Gold Beige": ["Gold", "Beige"],
    "Gold Rose": ["Gold", "Red"],
    "Natural": ["Natural"],
    "Natural Ash": ["Natural", "Ash"],
    "Natural Warm": ["Natural", "Warm"],
    "Natural Beige": ["Natural", "Beige"],
    "Natural Natural": ["Natural", "Neutral"],
    "Neutral": ["Natural", "Neutral"],
    "Ash": ["Ash"],
    "Ash Blue": ["Ash", "Blue"],
    "Ash Brown": ["Ash", "Brown"],
    "Ash Gold": ["Ash", "Gold"],
    "Blue": ["Blue"],
    "Blue-Violet": ["Blue", "Violet"],
    "Blue-Green": ["Blue", "Green"],
    "Violet": ["Violet"],
    "Violet Violet": ["Violet"],
    "Violet Gold": ["Violet", "Gold"],
    "Violet-Blue": ["Violet", "Blue"],
    "Copper": ["Copper"],
    "Copper Brown": ["Copper", "Brown", "Warm"],
    "Copper Red": ["Copper", "Red"],
    "Red": ["Red"],
    "Red Orange": ["Red", "Copper"],
    "Red Red": ["Red"],
    "Red-Violet": ["Red", "Violet"],
    "Red-Mahogany": ["Red", "Mahogany"],
    "Mahogany": ["Mahogany", "Red"],
    "Auburn Accent": ["Red", "Copper"],
    "Silver/Blue": ["Ash", "Blue"],
    "Grey": ["Other"],
    "Grey-Violet": ["Violet", "Other"],
    "Matte": ["Green"],
    "Green": ["Green"],
    "Beige": ["Beige", "Gold"],
    "Chocolate": ["Brown", "Warm"],
    "Coppers": ["Copper"],
    "Golds": ["Gold"],
    "Reds": ["Red"],
    "Naturals": ["Natural", "Neutral"],
    "Cool Browns & Blondes": ["Ash", "Blue"],
    "Warm Browns & Blondes": ["Gold", "Warm"],
    # Pravana ChromaSilk inventory families
    "Lowlight": ["Gold", "Copper", "Natural"],
    "Cool Fashion": ["Ash", "Violet"],
    "Fashion Brown": ["Gold", "Beige", "Ash"],
    "Beige": ["Beige", "Violet"],
    "Light Fashion Ash": ["Ash", "Beige", "Gold"],
    "Intense Ash": ["Ash", "Blue"],
    "Golden": ["Gold"],
    "Bombshell": ["Gold", "Violet"],
    "Cool Copper": ["Copper", "Mahogany"],
    "Vibrant Copper": ["Copper", "Red"],
    "Vibrant Red": ["Red"],
    "Neutral-Warm": ["Beige", "Gold"],
    "Additive": ["Other"],
}

# Aveda pure tone Tonal Direction (from inventory) → normalized
AVEDA_DIRECTION_TO_NORMALIZED: dict[str, list[str]] = {
    "Natural": ["Natural"],
    "Natural/Natural": ["Natural", "Neutral"],
    "Blue/Violet": ["Blue", "Violet", "Ash"],
    "Blue": ["Blue", "Ash"],
    "Blue/Green": ["Blue", "Green", "Ash"],
    "Yellow/Orange": ["Gold", "Copper"],
    "Orange/Red": ["Copper", "Red"],
    "Red/Orange": ["Red", "Copper"],
    "Violet/Red": ["Violet", "Red"],
    "Red": ["Red"],
    "Intense Ash": ["Ash", "Blue"],
    "Intense Copper": ["Copper", "Red"],
    "Intense Violet/Red": ["Violet", "Red"],
    "Intense Red": ["Red"],
}

# L'Oréal tonal_reference_key Tonal Family column → normalized
LOREAL_FAMILY_TO_NORMALIZED: dict[str, list[str]] = {
    "Natural": ["Natural"],
    "Blue": ["Blue", "Ash"],
    "Violet": ["Violet"],
    "Yellow": ["Gold"],
    "Orange": ["Copper"],
    "Red": ["Red"],
    "Red-Violet": ["Red", "Violet"],
    "Green": ["Green"],
    "Grey": ["Other"],
    "Chocolate": ["Brown", "Warm"],
}
