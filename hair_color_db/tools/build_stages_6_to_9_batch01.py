#!/usr/bin/env python3
"""Build Batch 1 Stage 6-9 artifacts from Stage 4-5 raw extractions.

Stage 6: manufacturer_tone_reference  (decode each line's own tone notation)
Stage 7: tone_normalization_map       (auditable mapping to the normalized taxonomy)
Stage 8: normalized_shade_records     (merge raw + line defaults + tone map)
Stage 9: qa_findings                  (integrity checks)

All inferred meanings are flagged; nothing is asserted without either a printed
legend (confirmed) or explicit shade-name evidence captured in the rationale.
"""
import json, glob, os, re
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), '..')
B1 = os.path.join(BASE, 'batches', 'batch01')

TAXONOMY = {"Natural","Neutral","Ash","Blue","Green","Violet","Pearl","Gold","Beige",
            "Copper","Red","Mahogany","Mocha","Brown","Warm","Cool","Other"}

raw, line_tech = [], []
for f in sorted(glob.glob(os.path.join(B1, '*_raw_shade_records.json'))):
    raw += json.load(open(f))['raw_shade_records']
for f in sorted(glob.glob(os.path.join(B1, '*_line_technical_records.json'))):
    line_tech += json.load(open(f))['line_technical_records']
tech_by_key = {t['canonical_key']: t for t in line_tech}

# ---------------------------------------------------------------------------
# Legend-confirmed digit systems (verbatim meanings from the printed legends in
# the Stage 5 line technical records; normalized tones chosen from taxonomy).
WELLA_DIGITS = {
    '0': ('Natural', ['Natural'], 'Pure Naturals family; /0 codes printed under Pure Naturals in official leaflet'),
    '1': ('Ash (blue/green)', ['Ash','Blue','Green'], 'printed legend'),
    '2': ('Matt (green)', ['Green'], 'printed legend; Matt not in taxonomy, mapped to its stated green undertone'),
    '3': ('Gold (yellow)', ['Gold'], 'printed legend'),
    '4': ('Red (warm)', ['Red','Warm'], 'printed legend'),
    '5': ('Mahogany (red/violet)', ['Mahogany','Red','Violet'], 'printed legend'),
    '6': ('Violet (cool)', ['Violet','Cool'], 'printed legend'),
    '7': ('Brown (red, yellow, blue)', ['Brown'], 'printed legend'),
    '8': ('Pearl (blue)', ['Pearl','Blue'], 'printed legend'),
    '9': ('Cendre (blue/violet)', ['Ash','Blue','Violet'], 'printed legend; Cendre not in taxonomy, mapped to Ash plus stated blue/violet undertones'),
}
SKP_DIGITS = {
    '0': ('Natural (neutral)', ['Natural','Neutral'], 'printed legend'),
    '1': ('Cendré (blue/violet)', ['Ash','Blue','Violet'], 'printed legend; Cendré not in taxonomy, mapped to Ash plus stated blue/violet undertones'),
    '2': ('Ash (blue)', ['Ash','Blue'], 'printed legend'),
    '3': ('Matte (green)', ['Green'], 'printed legend; Matte not in taxonomy, mapped to its stated green undertone'),
    '4': ('Beige (muted gold)', ['Beige','Gold'], 'printed legend'),
    '5': ('Gold', ['Gold'], 'printed legend'),
    '6': ('Chocolate (warm brown)', ['Brown','Warm'], 'printed legend'),
    '7': ('Copper (orange)', ['Copper'], 'printed legend'),
    '8': ('Red', ['Red'], 'printed legend'),
    '9': ('Violet', ['Violet'], 'printed legend'),
}
# Redken letter codes. status: confirmed = printed legend in Stage 5 records;
# inferred = decoded from official shade-name evidence only (evidence quoted).
SEQ = {
 'T':  ('confirmed','Titanium', ['Blue','Cool'], "Legend: Titanium (printed tone Silver/Blue); shade names Platinum/Chrome/Silver/Steel/Iron"),
 'B':  ('confirmed','Blue', ['Blue'], 'Legend: Blue'),
 'V':  ('confirmed','Violet', ['Violet'], 'Legend: Violet'),
 'GN': ('confirmed','Green Natural', ['Green','Natural'], 'Legend: Green Natural (Green/Yellow)'),
 'N':  ('confirmed','Natural', ['Natural'], 'Legend: Natural'),
 'NB': ('confirmed','Neutral Brown', ['Neutral','Brown'], 'Legend (2013 AU chart, flagged in Stage 4 issue log): Neutral Brown Blonde'),
 'GB': ('confirmed','Gold Beige', ['Gold','Beige'], 'Legend: Gold Beige (Gold/Mauve)'),
 'G':  ('confirmed','Gold', ['Gold'], 'Legend: Gold (Yellow)'),
 'GG': ('confirmed','Gold Gold', ['Gold'], 'Legend: Gold Gold (Yellow Yellow)'),
 'WG': ('confirmed','Warm Gold', ['Warm','Gold'], 'Legend: Warm Gold (Yellow/Orange)'),
 'C':  ('confirmed','Copper', ['Copper'], 'Legend: Copper (Orange)'),
 'CC': ('confirmed','Copper Copper', ['Copper'], 'Legend: Copper Copper (Orange/Orange)'),
 'CB': ('confirmed','Copper Brown', ['Copper','Brown'], 'Legend: Copper Brown (Red/Orange)'),
 'RB': ('confirmed','Red Brown', ['Red','Brown'], 'Legend: Red Brown (Red)'),
 'R':  ('confirmed','Red', ['Red'], 'Legend: Red'),
 'RV': ('confirmed','Red Violet', ['Red','Violet'], 'Legend: Red Violet (Red/Violet)'),
 'MV': ('confirmed','Mahogany Violet', ['Mahogany','Violet'], 'Legend: Mahogany Violet (Violet/Red)'),
 'NA': ('inferred','Natural Ash (inferred)', ['Natural','Ash'], "No printed legend; inferred from official shade names: Marble, Mist, Volcanic, Pewter, Granite, Smoke"),
 'NW': ('inferred','Natural Warm (inferred)', ['Natural','Warm'], "No printed legend; inferred from official shade names: Cream Soda, Milk Tea, Macchiato, Cocoa Bean"),
 'NCh':('inferred','Natural Chocolate (inferred)', ['Natural','Brown','Warm'], "No printed legend; inferred from official shade names: Fondue, Ganache, Dark Chocolate"),
 'P':  ('inferred','Pearl (inferred)', ['Pearl'], "No printed legend; inferred from official shade names: Ivory Pearl, Opal Glow, Mother of Pearl"),
 'CR': ('inferred','Copper Red (inferred)', ['Copper','Red'], "No printed legend; inferred from official shade names: Sunrise, Sunset"),
 'VB': ('inferred','Violet Blue (inferred)', ['Violet','Blue'], "No printed legend; inferred from official shade names: Violet Frost, Violet Star, Violet Lagoon"),
 'VV': ('inferred','Violet Violet (inferred)', ['Violet'], "No printed legend; inferred from official shade name: Lavender Ice"),
 'VG': ('inferred','Violet Gold (inferred)', ['Violet','Gold'], "No printed legend; inferred from official shade names: Iridescence, Gilded Taupe"),
 'AG': ('inferred','Ash Gold (inferred)', ['Ash','Gold'], "No printed legend; inferred from official shade names: Misty Beige, Glossy Greige, Smokey Beige (greige = ash+gold)"),
 'M':  ('inferred','Mocha (inferred, ambiguous)', ['Mocha'], "No printed legend; names Sand Dunes/Driftwood/Smoked Cedar/Midnight Ash are smoky-neutral; mapped to Mocha per family naming, flagged ambiguous"),
 'ABn':('inferred','Ash Brown (inferred from sibling line legend)', ['Ash','Brown'], "No SEQ legend; Color Gels Lacquers legend defines ABn = Ash Brown; cross-line reuse is inferred per spec rule"),
 'RR': ('inferred','Red Red (inferred from sibling line legend)', ['Red'], "No SEQ legend; Color Gels Lacquers legend defines RR = Red Red; cross-line reuse is inferred per spec rule"),
 'VRo':('inferred','Violet Rose (inferred from sibling line legend)', ['Violet','Other'], "No SEQ legend; Color Gels Lacquers legend defines VRo = Violet Rose; cross-line reuse is inferred per spec rule"),
 'GI': (None, None, None, "No printed legend; shade names (Tahitian Sand, Hamptons, St. Barths, Tenerife) do not unambiguously identify a tone family"),
 'AA': (None, None, None, "No printed legend; shade names (Papaya, Bonfire) suggest warm/copper but contradict conventional 'AA = intense ash' reading; unresolved"),
 'A':  (None, None, None, "No printed legend; single shade 03A Terra Cotta (warm name) contradicts conventional 'A = Ash'; unresolved"),
}
CGL = {
 'GN': ('confirmed','Green Natural', ['Green','Natural'], 'Legend: Green Natural - Controls unwanted red tones when lifting'),
 'AB': ('confirmed','Ash Blue', ['Ash','Blue'], 'Legend: Ash Blue - maximum refinement of warmth'),
 'NA': ('confirmed','Natural Ash', ['Natural','Ash'], 'Legend: Natural Ash'),
 'ABn':('confirmed','Ash Brown', ['Ash','Brown'], 'Legend: Ash Brown - ultra-cool ash brunette'),
 'N':  ('confirmed','Natural', ['Natural'], 'Legend: Natural'),
 'NN': ('confirmed','Natural Natural', ['Natural','Neutral'], 'Legend: Natural Natural - extreme coverage neutral tones'),
 'GB': ('confirmed','Gold Beige', ['Gold','Beige'], 'Legend: Gold Beige'),
 'NW': ('confirmed','Natural Warm', ['Natural','Warm'], 'Legend: Natural Warm'),
 'NG': ('confirmed','Natural Gold', ['Natural','Gold'], 'Legend: Natural Gold'),
 'WG': ('confirmed','Warm Gold', ['Warm','Gold'], 'Legend: Warm Gold'),
 'CB': ('confirmed','Copper Brown', ['Copper','Brown'], 'Legend: Copper Brown'),
 'RB': ('confirmed','Ruby Brown', ['Red','Brown'], 'Legend: Ruby Brown - soft ruby-like results'),
 'RO': ('confirmed','Red Orange', ['Red','Copper'], 'Legend: Red Orange; Orange not in taxonomy, mapped to Copper (orange undertone family)'),
 'RR': ('confirmed','Red Red', ['Red'], 'Legend: Red Red'),
 'RV': ('confirmed','Red Violet', ['Red','Violet'], 'Legend: Red Violet'),
 'VRo':('confirmed','Violet Rose', ['Violet','Other'], 'Legend: Violet Rose; Rose not in taxonomy, secondary mapped to Other'),
}

LINE_SYSTEM = {
 'Redken::Shades EQ Gloss::US': ('letters', SEQ),
 'Redken::Color Gels Lacquers::US': ('letters', CGL),
 'Wella Professionals::Koleston Perfect::US': ('digits', WELLA_DIGITS),
 'Wella Professionals::Color Touch::US': ('digits', WELLA_DIGITS),
 'Schwarzkopf Professional::IGORA ROYAL::US': ('digits', SKP_DIGITS),
 'Schwarzkopf Professional::IGORA VIBRANCE::US': ('digits', SKP_DIGITS),
}

# observed tone codes per line
observed = defaultdict(set)
for r in raw:
    for c in r['manufacturer_tone_codes']:
        observed[r['canonical_key']].add(c)

tone_reference, ambiguous_codes = [], []
norm_map, unresolved = [], []

for key, codes in sorted(observed.items()):
    system, table = LINE_SYSTEM[key]
    tech = tech_by_key.get(key, {})
    src_url = tech.get('source_url',''); src_doc = tech.get('source_document','')
    brand, line = key.split('::')[0], key.split('::')[1]
    for code in sorted(codes):
        if system == 'letters':
            entry = table.get(code)
            if entry is None or entry[0] is None:
                reason = entry[3] if entry else 'Code observed but absent from all printed legends and not safely inferable.'
                tone_reference.append({
                    'canonical_key': key, 'brand': brand, 'product_line': line,
                    'manufacturer_tone_code': code, 'manufacturer_term': None,
                    'manufacturer_definition': None,
                    'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                    'confidence': 'unresolved', 'notes_on_ambiguity': [reason]})
                ambiguous_codes.append({'canonical_key': key, 'manufacturer_tone_code': code,
                    'ambiguity_reason': 'no_printed_legend_and_no_safe_inference', 'details': reason})
                unresolved.append({'canonical_key': key, 'manufacturer_tone_code': code,
                    'reason': 'tone_meaning_unresolved', 'details': reason})
                continue
            status, term, tones, rationale = entry
            conf = 'high' if status == 'confirmed' else 'medium'
            flag = status != 'confirmed' or 'ambiguous' in (term or '')
            tone_reference.append({
                'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': term,
                'manufacturer_definition': rationale,
                'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                'confidence': conf,
                'notes_on_ambiguity': ([] if status=='confirmed' else [rationale])})
            norm_map.append({
                'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': term,
                'normalized_tones': tones, 'mapping_rationale': rationale,
                'mapping_confidence': conf, 'ambiguity_flag': bool(flag), 'notes': []})
        else:  # digit systems (Wella '/xy', SKP 'xy')
            digits = re.sub(r'\D','', code)
            if not digits:
                continue
            parts, tones, defs, ok = [], [], [], True
            for i, d in enumerate(digits):
                if d not in table:
                    ok = False; break
                term_d, tones_d, why = table[d]
                role = ['primary','secondary','tertiary'][min(i,2)]
                parts.append(f"{role} {d} = {term_d}")
                defs.append(why)
                for t in tones_d:
                    if t not in tones:
                        tones.append(t)
            definition = '; '.join(parts)
            three = len(digits) >= 3
            conf = 'high' if not three else 'medium'
            notes = []
            if three:
                notes.append('Three tone digits observed (special/Absolutes-style code); per-digit decoding applied but the third digit role is not documented in fetched sources.')
            tone_reference.append({
                'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': None,
                'manufacturer_definition': definition,
                'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                'confidence': conf, 'notes_on_ambiguity': notes})
            if three:
                ambiguous_codes.append({'canonical_key': key, 'manufacturer_tone_code': code,
                    'ambiguity_reason': 'undocumented_third_digit', 'details': notes[0]})
            norm_map.append({
                'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': None,
                'normalized_tones': tones,
                'mapping_rationale': f"Per-digit decode via printed line legend: {definition}",
                'mapping_confidence': conf, 'ambiguity_flag': three, 'notes': notes})

assert all(set(m['normalized_tones']) <= TAXONOMY for m in norm_map)

json.dump({'stage': 6, 'artifact': 'manufacturer_tone_reference', 'batch': 1,
           'completion_status': 'complete',
           'manufacturer_tone_reference': tone_reference,
           'ambiguous_tone_codes': ambiguous_codes,
           'issue_log': [
             {'item': 'Shades EQ legend provenance', 'issue_type': 'source_recency',
              'details': 'Part of the SEQ letter legend comes from a 2013 AU official chart; US 2022 chart did not pair words with all codes. Cross-region reuse flagged in confidence.'},
             {'item': 'Cendre/Matt translation', 'issue_type': 'taxonomy_translation',
              'details': 'Cendre/Cendré and Matt/Matte are not taxonomy terms; mapped to Ash/Green with the manufacturer wording preserved in definitions.'}]},
          open(os.path.join(B1,'tone_reference_stage6.json'),'w'), indent=2, ensure_ascii=False)

json.dump({'stage': 7, 'artifact': 'tone_normalization_map', 'batch': 1,
           'completion_status': 'complete',
           'tone_normalization_map': norm_map,
           'unresolved_mappings': unresolved,
           'issue_log': []},
          open(os.path.join(B1,'tone_normalization_map_stage7.json'),'w'), indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- Stage 8
map_idx = {(m['canonical_key'], m['manufacturer_tone_code']): m for m in norm_map}
normalized, merge_issues = [], []
for r in raw:
    key = r['canonical_key']; tech = tech_by_key.get(key, {})
    tones, gaps, assumptions = [], list(r.get('data_gaps') or []), list(r.get('assumptions') or [])
    for c in r['manufacturer_tone_codes']:
        m = map_idx.get((key, c))
        if m:
            for t in m['normalized_tones']:
                if t not in tones: tones.append(t)
        else:
            gaps.append(f'tone code {c} unresolved; no normalized tones assigned for it')
    mixing = r.get('mixing_ratio')
    if mixing is None and tech.get('default_mixing_ratio') and tech.get('evidence_status') in ('confirmed','partially_confirmed'):
        mixing = tech['default_mixing_ratio']
        assumptions.append('mixing_ratio inherited from line-level default (Stage 5 record)')
    devs = r.get('developer_recommendations') or []
    if not devs and tech.get('developer_options'):
        devs = tech['developer_options']
        assumptions.append('developer_options inherited from line-level record (Stage 5)')
    ctype = r.get('color_type') or tech.get('color_type')
    normalized.append({
        'canonical_key': key, 'brand': r['brand'], 'product_line': r['product_line'],
        'shade_code': r['shade_code'], 'shade_name': r['shade_name'], 'level': r['level'],
        'manufacturer_tone_codes': r['manufacturer_tone_codes'],
        'manufacturer_tone_descriptions': r['manufacturer_tone_descriptions'],
        'normalized_tones': tones, 'color_type': ctype,
        'gray_coverage_claim': r.get('gray_coverage_claim'),
        'lift_levels': r.get('lift_capability'),
        'mixing_ratio': mixing, 'developer_options': devs,
        'processing_time_minutes': r.get('processing_time_minutes'),
        'special_usage_notes': r.get('special_usage_notes'),
        'official_swatch_image_exists': r.get('official_swatch_image_exists'),
        'region_or_market': r.get('region_or_market'),
        'discontinued_status': tech.get('discontinued_status'),
        'source_url': r['source_url'], 'source_document': r['source_document'],
        'source_type': r['source_type'], 'source_publication_date': r.get('source_publication_date'),
        'source_confidence': r['source_confidence'], 'evidence_status': r['evidence_status'],
        'assumptions': assumptions, 'data_gaps': gaps})
    if not r['manufacturer_tone_codes'] and r['shade_code'] not in ('000','Clear','0-00'):
        merge_issues.append({'canonical_key': key, 'shade_code': r['shade_code'],
            'issue_type': 'no_tone_codes', 'details': 'Raw record carries no manufacturer tone codes; normalized_tones left empty.'})

json.dump({'stage': 8, 'artifact': 'normalized_shade_records', 'batch': 1,
           'completion_status': 'complete',
           'normalized_shade_records': normalized, 'merge_issues': merge_issues,
           'issue_log': []},
          open(os.path.join(B1,'normalized_shade_records_stage8.json'),'w'), indent=2, ensure_ascii=False)

# ---------------------------------------------------------------- Stage 9 QA
findings, fixes = [], []
seen = defaultdict(list)
for n in normalized:
    seen[(n['canonical_key'], n['shade_code'])].append(n)
for (key, code), rows in seen.items():
    if len(rows) > 1:
        findings.append({'canonical_key': key, 'record_ref': code, 'issue_type': 'duplicate_shade_code',
            'severity': 'high', 'details': f'{len(rows)} normalized records share shade_code {code}',
            'recommended_fix': 'Deduplicate or distinguish sub-range variants explicitly.'})
for n in normalized:
    ref = f"{n['canonical_key']}#{n['shade_code']}"
    if not n['source_url']:
        findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref,
            'issue_type': 'missing_provenance', 'severity': 'high',
            'details': 'source_url empty', 'recommended_fix': 'Re-extract with source captured.'})
    if n['level'] is not None and n['shade_code']:
        mnum = re.match(r'^0*(\d+(?:[.,]5)?)', str(n['shade_code']))
        if mnum:
            lvl = float(mnum.group(1).replace(',', '.'))
            if abs(lvl - float(n['level'])) > 0.01:
                findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref,
                    'issue_type': 'level_code_mismatch', 'severity': 'medium',
                    'details': f"level field {n['level']} vs code prefix {lvl}",
                    'recommended_fix': 'Verify against source swatch chart.'})
    if n['manufacturer_tone_codes'] and not n['normalized_tones']:
        findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref,
            'issue_type': 'unmapped_tone_codes', 'severity': 'medium',
            'details': f"codes {n['manufacturer_tone_codes']} have no normalized mapping",
            'recommended_fix': 'Resolve via official tone legend retrieval (see unresolved_mappings).'})
    if n['evidence_status'] not in ('confirmed','partially_confirmed','inferred','conflicting','missing','unresolved'):
        findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref,
            'issue_type': 'invalid_enum', 'severity': 'medium',
            'details': f"evidence_status={n['evidence_status']}", 'recommended_fix': 'Normalize enum.'})

# count-vs-claim checks (claims observed in Stage 1/4 sources)
claims = {'Schwarzkopf Professional::IGORA ROYAL::US': 143,
          'Schwarzkopf Professional::IGORA VIBRANCE::US': 68}
per_line = defaultdict(int)
for n in normalized: per_line[n['canonical_key']] += 1
for key, claim in claims.items():
    got = per_line[key]
    if got != claim:
        findings.append({'canonical_key': key, 'record_ref': 'line_total',
            'issue_type': 'count_vs_manufacturer_claim', 'severity': 'medium',
            'details': f'extracted {got} records vs manufacturer-claimed {claim} shades',
            'recommended_fix': 'Pull newer official chart or per-sub-range pages to close the count gap.'})

json.dump({'stage': 9, 'artifact': 'qa_findings', 'batch': 1,
           'completion_status': 'complete',
           'qa_findings': findings,
           'corrected_records_recommendations': fixes,
           'unresolved_issues': [u for u in unresolved],
           'issue_log': [],
           'record_counts_by_line': dict(per_line)},
          open(os.path.join(B1,'qa_findings_stage9.json'),'w'), indent=2, ensure_ascii=False)

print('stage6 tone refs:', len(tone_reference), '| ambiguous:', len(ambiguous_codes))
print('stage7 mappings:', len(norm_map), '| unresolved:', len(unresolved))
print('stage8 normalized:', len(normalized), '| merge issues:', len(merge_issues))
print('stage9 findings:', len(findings))
for f_ in findings[:25]:
    print('  -', f_['issue_type'], f_['record_ref'], '|', f_['details'][:90])
