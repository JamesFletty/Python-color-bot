#!/usr/bin/env python3
"""Build Batch 3 Stage 6-9 artifacts (Pravana + Goldwell line tech)."""
import json, glob, os, re
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), '..')
B3 = os.path.join(BASE, 'batches', 'batch03')
TAXONOMY = {"Natural", "Neutral", "Ash", "Blue", "Green", "Violet", "Pearl", "Gold", "Beige",
            "Copper", "Red", "Mahogany", "Mocha", "Brown", "Warm", "Cool", "Other"}

raw, line_tech = [], []
for f in sorted(glob.glob(os.path.join(B3, '*_raw_shade_records.json'))):
    raw += json.load(open(f))['raw_shade_records']
for f in sorted(glob.glob(os.path.join(B3, '*_line_technical_records.json'))):
    line_tech += json.load(open(f))['line_technical_records']
tech_by_key = {t['canonical_key']: t for t in line_tech}

# Pravana Creme digit/combo codes — rationales sourced from official product page descriptions observed in Batch 3 extraction.
PRAVANA_CREME = {
    '0': ('Natural/Neutral base', ['Natural', 'Neutral'], "product pages describe .0 / NN / neutral family bases"),
    '1': ('Ash', ['Ash', 'Green', 'Cool'], "Ash Family: 'cool green base' (printed on Ash family product pages)"),
    '2': ('Beige (intense)', ['Beige'], "product pages: '.22 intense beige' / Beige family descriptions"),
    '3': ('Gold', ['Gold'], "Chocolate/Gold family pages: gold tonal value percentages"),
    '4': ('Copper', ['Copper'], "Copper family: 'blended orange base' / 100% copper tonal value"),
    '5': ('Mahogany', ['Mahogany', 'Red'], "Chocolate family blends with Mahogany percentages on product pages"),
    '6': ('Red', ['Red'], "Red family positioning on product pages"),
    '7': ('Violet', ['Violet'], "Violet family / violet tonal descriptions on product pages"),
    '8': ('Pearl/Mocha', ['Pearl', 'Mocha'], "Pearl series description on product pages; Mocha used for brunette mocha series — flagged ambiguous"),
    '9': ('Intense/Extra (series)', ['Other'], "x.99 and intense series described on product pages; exact pigment not uniformly named — flagged"),
    '02': ('Sheer Beige', ['Beige'], "10.02: 'sheer beige base' (printed)"),
    '03': ('Gold Beige', ['Gold', 'Beige'], "inferred from Beige/Gold family wording on related shades — flagged"),
    '08': ('Pearl', ['Pearl'], "Pearl series: 'softer silver and pink balanced hues' (printed)"),
    '12': ('Ash + Beige', ['Ash', 'Beige'], "9.12: '70% Ash 30% Beige' (printed)"),
    '13': ('Ash + Gold', ['Ash', 'Gold'], "Ash family + gold tonal descriptions on related shades — partially confirmed"),
    '20': ('Intense Beige', ['Beige'], "4.20 / bright beige descriptions on product pages"),
    '22': ('Intense Beige', ['Beige'], "x.22 intense beige wording on product pages"),
    '23': ('Beige + Gold', ['Beige', 'Gold'], "6.23 beige golden descriptions"),
    '35': ('Gold + Mahogany', ['Gold', 'Mahogany'], "6.35: '70% Gold and 30% Mahogany' (printed)"),
    '37': ('Gold + Violet', ['Gold', 'Violet'], "4.37: '70% Gold and 30% Violet' (printed)"),
    '52': ('Mahogany + Beige', ['Mahogany', 'Beige'], "mahogany beige descriptions on product pages"),
    '56': ('Mahogany + Red', ['Mahogany', 'Red'], "mahogany red descriptions on product pages"),
    '66': ('Intense Red', ['Red'], "4.66 intense red descriptions on product pages"),
    '72': ('Violet + Beige', ['Violet', 'Beige'], "10.72: '100% Violet and 30% Beige' (printed)"),
    '77': ('Deep Chroma series', ['Other'], "Deep Chroma Collection positioning on product pages; exact pigment split not stated per shade — flagged"),
    '91': ('Metallic finish series', ['Other'], "10.91: 'metallic finish on level 10 and grey hair' (printed)"),
    '92': ('Smokey Beige', ['Beige', 'Neutral'], "5.92/8.92: 'Smokey Beige' neutralizing tone (printed)"),
    '07': ('Sheer Violet', ['Violet'], "10.07: 'cool violet base' / Violet (.7) family (printed)"),
    '11': ('Intense Ash', ['Ash', 'Green', 'Cool'], "Intense Ash family: 'cool double green base with 200% cool green tonal value' (printed)"),
    '31': ('Gold + Ash', ['Gold', 'Ash'], "x.31: '70% Gold and 30% Ash' (printed)"),
    '34': ('Gold + Copper', ['Gold', 'Copper'], "x.34: '70% Gold and 30% Copper' (printed)"),
    '40': ('Bright Copper', ['Copper'], "7.40: 'bright Copper' (printed)"),
    '43': ('Copper + Gold', ['Copper', 'Gold'], "x.43: '70% copper and 30% Gold' / Copper+Gold variants (printed)"),
    '44': ('Intense Copper', ['Copper'], "7.44: '200% Copper for intense copper' (printed)"),
    '45': ('Copper + Mahogany', ['Copper', 'Mahogany'], "Rich Copper Family: '70% Copper and 30% Mahogany' (printed)"),
    '46': ('Copper + Red', ['Copper', 'Red'], "x.46: '70% Copper and 30% Red' (printed)"),
    '62': ('Red + Beige', ['Red', 'Beige'], "x.62: '70% Red and 30% Beige' (printed)"),
    '64': ('Red + Copper', ['Red', 'Copper'], "x.64: '70% Red and 30% Copper' (printed)"),
    '99': ('Intense series', ['Other'], "3.99 intense series — exact tone name varies; flagged"),
}

PRAVANA_EXPRESS = {
    'Ash': ('Ash — cool/green base', ['Ash', 'Green', 'Cool'], "meta: 'cool/green base' (printed)"),
    'Beige': ('Beige', ['Beige'], "shade name as printed"),
    'Pearl': ('Pearl', ['Pearl'], "shade name as printed"),
    'Violet': ('Violet', ['Violet'], "shade name as printed"),
    'Rose Gold': ('Rose Gold', ['Gold', 'Copper', 'Warm'], "shade name; Gold/Copper inferred — flagged"),
    'Smokey Silver': ('Smokey Silver', ['Other', 'Cool'], "functional name; Silver not in taxonomy"),
    'Clear': ('Clear', [], "non-pigmented diluter"),
    'After Dark Mahogany': ('After Dark Mahogany', ['Mahogany'], "printed shade name"),
    'After Dark Neutral Ash': ('After Dark Neutral Ash', ['Neutral', 'Ash'], "printed shade name"),
    'After Dark Neutral Pearl': ('After Dark Neutral Pearl', ['Neutral', 'Pearl'], "printed shade name"),
}

def vivids_map(code, desc):
    c = code.lower()
    mapping = {
        'violet': (['Violet'], 'shade name'),
        'purple': (['Violet'], 'shade name'),
        'blue': (['Blue'], 'shade name'),
        'green': (['Green'], 'shade name'),
        'red': (['Red'], 'shade name'),
        'magenta': (['Red', 'Violet'], 'shade name'),
        'pink': (['Red'], 'shade name'),
        'orange': (['Copper'], 'shade name'),
        'yellow': (['Gold'], 'shade name'),
        'silver': (['Other', 'Cool'], 'Silver not in taxonomy'),
        'smokey silver': (['Other', 'Cool'], 'functional silver tone'),
        'smokey violet': (['Violet', 'Cool'], 'shade name'),
        'black': (['Other'], 'direct dye black'),
        'clear': ([], 'diluter/clear'),
        'aquamarine': (['Blue', 'Green'], 'shade name'),
        'emerald': (['Green'], 'shade name'),
        'garnet': (['Red', 'Mahogany'], 'shade name'),
        'grape': (['Violet'], 'shade name'),
        'crush': (['Red'], 'shade name'),
        'flame': (['Copper', 'Red'], 'shade name'),
        'neon': (['Other'], 'Neons sub-range label'),
    }
    for k, (tones, why) in mapping.items():
        if k in c:
            return tones, why, k in ('silver', 'smokey silver', 'rose gold')
    return ['Other'], 'direct dye shade name not mapped to standard tone family', True

observed = defaultdict(set)
for r in raw:
    key = r['canonical_key']
    if r['manufacturer_tone_codes']:
        for c in r['manufacturer_tone_codes']:
            observed[key].add(c)
    elif key == 'Pravana::ChromaSilk VIVIDS::US':
        observed[key].add(r['shade_code'])
    elif key == 'Pravana::ChromaSilk Express Tones::US':
        observed[key].add(r['shade_code'])

tone_reference, norm_map, unresolved, ambiguous_codes = [], [], [], []

for key in sorted(observed):
    brand, line = key.split('::')[0], key.split('::')[1]
    tech = tech_by_key.get(key, {})
    src_url, src_doc = tech.get('source_url', ''), tech.get('source_document', '')
    for code in sorted(observed[key]):
        if key == 'Pravana::ChromaSilk Creme Color::US':
            if code not in PRAVANA_CREME:
                reason = f"reflect code {code!r} has no mapping table entry; needs Product Knowledge Guide PDF"
                tone_reference.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                    'manufacturer_tone_code': code, 'manufacturer_term': None, 'manufacturer_definition': None,
                    'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                    'confidence': 'unresolved', 'notes_on_ambiguity': [reason]})
                unresolved.append({'canonical_key': key, 'manufacturer_tone_code': code, 'reason': 'tone_meaning_unresolved', 'details': reason})
                continue
            term, tones, why = PRAVANA_CREME[code]
            flag = code in ('8', '9', '03', '99') or '+' in code
            conf = 'high' if code in ('1', '4', '12', '35', '37', '02', '08', '22', '20') else 'medium'
            tone_reference.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': term, 'manufacturer_definition': why,
                'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                'confidence': conf, 'notes_on_ambiguity': ([] if not flag else [why])})
            if flag:
                ambiguous_codes.append({'canonical_key': key, 'manufacturer_tone_code': code, 'ambiguity_reason': 'partial_legend', 'details': why})
            norm_map.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': term, 'normalized_tones': tones,
                'mapping_rationale': why, 'mapping_confidence': conf, 'ambiguity_flag': flag, 'notes': []})
        elif key == 'Pravana::ChromaSilk Express Tones::US':
            if code not in PRAVANA_EXPRESS:
                reason = f"Express Tones shade {code!r} not in legend table"
                tone_reference.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                    'manufacturer_tone_code': code, 'manufacturer_term': code, 'manufacturer_definition': None,
                    'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                    'confidence': 'medium', 'notes_on_ambiguity': [reason]})
                tones, term, why = [code], code, 'shade name as printed on official product page'
            else:
                term, tones, why = PRAVANA_EXPRESS[code]
                flag = code == 'Rose Gold'
                tone_reference.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                    'manufacturer_tone_code': code, 'manufacturer_term': term, 'manufacturer_definition': why,
                    'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                    'confidence': 'high', 'notes_on_ambiguity': ([] if not flag else [why])})
                norm_map.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                    'manufacturer_tone_code': code, 'manufacturer_term': term, 'normalized_tones': tones,
                    'mapping_rationale': why, 'mapping_confidence': 'high', 'ambiguity_flag': flag, 'notes': []})
                continue
            norm_map.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': term, 'normalized_tones': tones,
                'mapping_rationale': why, 'mapping_confidence': 'medium', 'ambiguity_flag': True, 'notes': []})
        elif key == 'Pravana::ChromaSilk VIVIDS::US':
            tones, why, flag = vivids_map(code, '')
            tone_reference.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': code, 'manufacturer_definition': why,
                'evidence_source_url': src_url, 'evidence_source_document': src_doc,
                'confidence': 'medium' if flag else 'high', 'notes_on_ambiguity': ([] if not flag else [why])})
            norm_map.append({'canonical_key': key, 'brand': brand, 'product_line': line,
                'manufacturer_tone_code': code, 'manufacturer_term': code, 'normalized_tones': tones,
                'mapping_rationale': why, 'mapping_confidence': 'medium' if flag else 'high',
                'ambiguity_flag': flag, 'notes': []})

assert all(set(m['normalized_tones']) <= TAXONOMY for m in norm_map)

json.dump({'stage': 6, 'artifact': 'manufacturer_tone_reference', 'batch': 3, 'completion_status': 'complete',
           'manufacturer_tone_reference': tone_reference, 'ambiguous_tone_codes': ambiguous_codes,
           'issue_log': [{'item': 'Pravana Creme multi-digit codes', 'issue_type': 'legend_gap',
                          'details': 'Full digit legend is in pro-gated Product Knowledge Guide PDF; mappings for combo codes derived from per-shade product page descriptions.'}]},
          open(os.path.join(B3, 'tone_reference_stage6.json'), 'w'), indent=2, ensure_ascii=False)

json.dump({'stage': 7, 'artifact': 'tone_normalization_map', 'batch': 3, 'completion_status': 'complete',
           'tone_normalization_map': norm_map, 'unresolved_mappings': unresolved, 'issue_log': []},
          open(os.path.join(B3, 'tone_normalization_map_stage7.json'), 'w'), indent=2, ensure_ascii=False)

map_idx = {(m['canonical_key'], m['manufacturer_tone_code']): m for m in norm_map}
normalized, merge_issues = [], []
for r in raw:
    key = r['canonical_key']
    tech = tech_by_key.get(key, {})
    tones, gaps, assumptions = [], list(r.get('data_gaps') or []), list(r.get('assumptions') or [])
    codes = r['manufacturer_tone_codes'] or ([r['shade_code']] if key != 'Pravana::ChromaSilk Creme Color::US' else [])
    for c in codes:
        m = map_idx.get((key, c))
        if m:
            for t in m['normalized_tones']:
                if t not in tones:
                    tones.append(t)
        else:
            gaps.append(f'tone code {c} unresolved; no normalized tones assigned')
    mixing = r.get('mixing_ratio')
    if mixing is None and tech.get('default_mixing_ratio'):
        mixing = tech['default_mixing_ratio']
        assumptions.append('mixing_ratio inherited from line-level default (Stage 5 record)')
    devs = r.get('developer_recommendations') or []
    if not devs and tech.get('developer_options'):
        devs = tech['developer_options']
        assumptions.append('developer_options inherited from line-level record (Stage 5)')
    normalized.append({
        'canonical_key': key, 'brand': r['brand'], 'product_line': r['product_line'],
        'shade_code': r['shade_code'], 'shade_name': r['shade_name'], 'level': r['level'],
        'manufacturer_tone_codes': r['manufacturer_tone_codes'] or codes,
        'manufacturer_tone_descriptions': r['manufacturer_tone_descriptions'],
        'normalized_tones': tones, 'color_type': r.get('color_type') or tech.get('color_type'),
        'gray_coverage_claim': r.get('gray_coverage_claim'), 'lift_levels': r.get('lift_capability'),
        'mixing_ratio': mixing, 'developer_options': devs,
        'processing_time_minutes': r.get('processing_time_minutes'),
        'special_usage_notes': r.get('special_usage_notes'),
        'official_swatch_image_exists': r.get('official_swatch_image_exists'),
        'region_or_market': r.get('region_or_market'),
        'discontinued_status': tech.get('discontinued_status'),
        'source_url': r['source_url'], 'source_document': r['source_document'],
        'source_type': r['source_type'], 'source_publication_date': r.get('source_publication_date'),
        'source_confidence': r['source_confidence'], 'evidence_status': r['evidence_status'],
        'assumptions': assumptions, 'data_gaps': gaps,
    })

json.dump({'stage': 8, 'artifact': 'normalized_shade_records', 'batch': 3, 'completion_status': 'complete',
           'normalized_shade_records': normalized, 'merge_issues': merge_issues, 'issue_log': []},
          open(os.path.join(B3, 'normalized_shade_records_stage8.json'), 'w'), indent=2, ensure_ascii=False)

findings = []
seen = defaultdict(list)
for n in normalized:
    seen[(n['canonical_key'], n['shade_code'])].append(n)
for (key, code), rows in seen.items():
    if len(rows) > 1:
        findings.append({'canonical_key': key, 'record_ref': code, 'issue_type': 'duplicate_shade_code',
            'severity': 'high', 'details': f'{len(rows)} normalized records share shade_code {code}',
            'recommended_fix': 'Distinguish sub-range variants or deduplicate.'})
for n in normalized:
    ref = f"{n['canonical_key']}#{n['shade_code']}"
    if not n['source_url']:
        findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref, 'issue_type': 'missing_provenance',
            'severity': 'high', 'details': 'source_url empty', 'recommended_fix': 'Re-extract with source captured.'})
    if n['manufacturer_tone_codes'] and not n['normalized_tones'] and 'clear' not in str(n['shade_code']).lower():
        findings.append({'canonical_key': n['canonical_key'], 'record_ref': ref, 'issue_type': 'unmapped_tone_codes',
            'severity': 'medium', 'details': f"codes {n['manufacturer_tone_codes']} have no normalized mapping",
            'recommended_fix': 'Resolve via official legend retrieval.'})

per_line = defaultdict(int)
for n in normalized:
    per_line[n['canonical_key']] += 1

json.dump({'stage': 9, 'artifact': 'qa_findings', 'batch': 3, 'completion_status': 'complete',
           'qa_findings': findings, 'corrected_records_recommendations': [],
           'unresolved_issues': unresolved, 'issue_log': [],
           'record_counts_by_line': dict(per_line)},
          open(os.path.join(B3, 'qa_findings_stage9.json'), 'w'), indent=2, ensure_ascii=False)

print('stage6', len(tone_reference), 'stage7', len(norm_map), 'unresolved', len(unresolved))
print('stage8', len(normalized), 'stage9 findings', len(findings))
for k, v in per_line.items():
    print(' ', k, v)
