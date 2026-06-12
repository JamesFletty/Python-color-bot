#!/usr/bin/env python3
"""Build Batch 2 Stage 6-9 artifacts (Matrix, L'Oréal Professionnel).

Same evidence discipline as batch 1: 'confirmed' = printed legend wording;
'inferred' = decoded from documented letter/digit conventions within the same
fetched documents, always flagged; unknown codes stay unresolved.
"""
import json, glob, os, re
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), '..')
B2 = os.path.join(BASE, 'batches', 'batch02')
TAXONOMY = {"Natural","Neutral","Ash","Blue","Green","Violet","Pearl","Gold","Beige",
            "Copper","Red","Mahogany","Mocha","Brown","Warm","Cool","Other"}

raw, line_tech = [], []
for f in sorted(glob.glob(os.path.join(B2, '*_raw_shade_records.json'))):
    raw += json.load(open(f))['raw_shade_records']
for f in sorted(glob.glob(os.path.join(B2, '*_line_technical_records.json'))):
    line_tech += json.load(open(f))['line_technical_records']
tech_by_key = {t['canonical_key']: t for t in line_tech}

# L'Oréal Professionnel reflect digits — printed legend on 2025 Majirel /
# Dia Light charts: .1 blue (B), .2 violet (V), .3 gold (G), .4 copper (C),
# .5 red-violet (Rv), .6 red (R), .7 green (Gr), .8 mocha (M); N natural.
LP_DIGITS = {
 '0': ('Natural (N)', ['Natural'], "printed legend lists 'N natural'; digit 0 in the reflect position denotes the natural reflect"),
 '1': ('blue (B)', ['Blue','Ash'], "printed legend '.1 blue (B)'; Ash added because the US dual letter code is B/Ash family — interpretation noted"),
 '2': ('violet (V)', ['Violet'], "printed legend '.2 violet (V)'"),
 '3': ('gold (G)', ['Gold'], "printed legend '.3 gold (G)'"),
 '4': ('copper (C)', ['Copper'], "printed legend '.4 copper (C)'"),
 '5': ('red-violet (Rv)', ['Red','Violet','Mahogany'], "printed legend '.5 red-violet (Rv)'; Mahogany added as the conventional name of the red-violet family — interpretation noted"),
 '6': ('red (R)', ['Red'], "printed legend '.6 red (R)'"),
 '7': ('green (Gr)', ['Green'], "printed legend '.7 green (Gr)'"),
 '8': ('mocha (M)', ['Mocha'], "printed legend '.8 mocha (M)'"),
}
# Matrix: manual prints digit legend (.0 Neutral ... .9 Pearl) and decodes
# example codes (4NJ: N primary tone, J secondary tone). US shades use letters.
MATRIX_LETTERS = {
 'N': ('confirmed','Neutral', ['Neutral'], "digit legend '.0 Neutral' + example decode (N = primary tone in 4NJ)"),
 'A': ('confirmed','Ash', ['Ash'], "digit legend '.1 Ash'"),
 'V': ('confirmed','Violet', ['Violet'], "digit legend '.2 Violet'"),
 'G': ('confirmed','Gold', ['Gold'], "digit legend '.3 Gold'"),
 'C': ('confirmed','Copper', ['Copper'], "digit legend '.4 Copper'"),
 'R': ('confirmed','Red', ['Red'], "digit legend '.6 Red'"),
 'J': ('inferred','Jade', ['Green'], "digit legend '.7 Jade' + J used as secondary tone in printed example 4NJ; Jade not in taxonomy, mapped to Green"),
 'M': ('inferred','Mocha (ambiguous vs Mahogany)', ['Mocha'], "digit legend lists both '.5 Mahogany' and '.8 Mocha'; letter M conventionally = Mocha in Matrix US naming — flagged ambiguous"),
 'P': ('inferred','Pearl', ['Pearl'], "digit legend '.9 Pearl'; letter P inferred as its initial"),
 'W': ('inferred','Warm', ['Warm'], "no printed letter legend; W inferred as Warm from NW/WN family convention — flagged"),
 'B': ('inferred','Brown (ambiguous vs Blue)', ['Brown'], "no printed letter legend; B in BR/BC/RB inferred as Brown — flagged; standalone word shades use full word BLUE for blue"),
}
MATRIX_SPECIAL = {
 'A+':  ('confirmed','Ash Plus', ['Ash'], "printed legend 'A+ (Ultra Blonde) = Ash Plus'"),
 'SR':  ('confirmed','SoRed booster', ['Red'], "printed legend 'SR = SoRed'"),
 'HD':  ('confirmed','High Definition', ['Other'], "printed legend 'HD = High Definition' (intensity series, not a tone family)"),
 'EBC': ('confirmed','Extra Blonding Cream (additive)', ['Other'], "printed legend: additive that disperses underlying pigment; not a tone"),
 'Clear': ('confirmed','Clear', [], "printed legend: reduces tonal deposit / adds shine; non-pigmented"),
 'RED': ('confirmed','Red (booster, printed word)', ['Red'], "shade printed as the word RED"),
 'BLUE': ('confirmed','Blue (booster, printed word)', ['Blue'], "shade printed as the word BLUE"),
 'Violet': ('confirmed','Violet (printed word)', ['Violet'], "shade printed as the word Violet"),
 'Silver': ('inferred','Silver (printed word)', ['Other','Cool'], "shade printed as the word Silver; Silver not in taxonomy"),
 'Anti-Brass': ('inferred','Anti-Brass fast toner', ['Other','Cool'], "functional neutralizer name as printed; underlying pigment not stated — flagged"),
 'Anti-Red': ('inferred','Anti-Red fast toner', ['Other','Cool'], "functional neutralizer name as printed; underlying pigment not stated — flagged"),
 'Anti-Yellow': ('inferred','Anti-Yellow fast toner', ['Other','Cool'], "functional neutralizer name as printed; underlying pigment not stated — flagged"),
}

def decode_matrix(code):
    """Return (status, term, tones, rationale) or None if unresolved."""
    if code in MATRIX_SPECIAL:
        return MATRIX_SPECIAL[code]
    body, plus = (code[:-1], True) if code.endswith('+') else (code, False)
    if body.startswith('SP'):  # Sheer Pastel + tone letter
        rest = body[2:]
        sub = decode_matrix(rest) if rest else ('confirmed','Sheer Pastel', [], 'printed legend')
        if sub is None: return None
        st, term, tones, why = sub
        return ('inferred', f'Sheer Pastel {term}', tones,
                f"printed legend 'Sheer Pastel (SP)' + {why}")
    letters = re.findall(r'[A-Z][a-z]*', body)
    if not letters or not all(l in MATRIX_LETTERS for l in letters):
        return None
    statuses, terms, tones, whys = [], [], [], []
    for i, l in enumerate(letters):
        st, term, t, why = MATRIX_LETTERS[l]
        statuses.append(st); whys.append(f"{l}={term} ({why})")
        role = 'primary' if i == 0 else 'secondary'
        terms.append(f"{role} {term}")
        for x in t:
            if x not in tones: tones.append(x)
    status = 'confirmed' if all(s == 'confirmed' for s in statuses) else 'inferred'
    term = ' / '.join(terms) + (' — intensified (+)' if plus else '')
    why = '; '.join(whys) + ("; '+' suffix = intensified series (legend shows A+ = Ash Plus)" if plus else '')
    return (status, term, tones, why)

observed = defaultdict(set)
for r in raw:
    for c in r['manufacturer_tone_codes']:
        observed[r['canonical_key']].add(c)

tone_reference, ambiguous_codes, norm_map, unresolved = [], [], [], []
for key, codes in sorted(observed.items()):
    brand, line = key.split('::')[0], key.split('::')[1]
    tech = tech_by_key.get(key, {})
    src_url, src_doc = tech.get('source_url',''), tech.get('source_document','')
    for code in sorted(codes):
        if brand == "L'Oréal Professionnel":
            digits = re.sub(r'\D','', code)
            parts, tones, ok = [], [], bool(digits)
            for i, d in enumerate(digits):
                if d not in LP_DIGITS: ok = False; break
                term_d, t, why = LP_DIGITS[d]
                parts.append(f"{['primary','secondary','tertiary'][min(i,2)]} .{d} = {term_d}")
                for x in t:
                    if x not in tones: tones.append(x)
            if not ok:
                reason = f'tone digits {code!r} not decodable via printed legend'
                tone_reference.append({'canonical_key':key,'brand':brand,'product_line':line,
                    'manufacturer_tone_code':code,'manufacturer_term':None,'manufacturer_definition':None,
                    'evidence_source_url':src_url,'evidence_source_document':src_doc,
                    'confidence':'unresolved','notes_on_ambiguity':[reason]})
                ambiguous_codes.append({'canonical_key':key,'manufacturer_tone_code':code,
                    'ambiguity_reason':'undecodable','details':reason})
                unresolved.append({'canonical_key':key,'manufacturer_tone_code':code,
                    'reason':'tone_meaning_unresolved','details':reason})
                continue
            definition = '; '.join(parts)
            interp = any(d in ('1','5','0') for d in digits)
            tone_reference.append({'canonical_key':key,'brand':brand,'product_line':line,
                'manufacturer_tone_code':code,'manufacturer_term':None,
                'manufacturer_definition':definition,
                'evidence_source_url':src_url,'evidence_source_document':src_doc,
                'confidence':'high','notes_on_ambiguity':(
                    ['Mapping for digits 0/1/5 includes conventional family names (Natural/Ash/Mahogany) beyond the literal printed words; see rationale.'] if interp else [])})
            norm_map.append({'canonical_key':key,'brand':brand,'product_line':line,
                'manufacturer_tone_code':code,'manufacturer_term':None,
                'normalized_tones':tones,
                'mapping_rationale':f'Per-digit decode via printed 2025 chart legend: {definition}',
                'mapping_confidence':'high','ambiguity_flag':False,'notes':[]})
        else:  # Matrix
            dec = decode_matrix(code)
            if dec is None:
                reason = f'letter code {code!r} not decodable from printed legend or documented conventions'
                tone_reference.append({'canonical_key':key,'brand':brand,'product_line':line,
                    'manufacturer_tone_code':code,'manufacturer_term':None,'manufacturer_definition':None,
                    'evidence_source_url':src_url,'evidence_source_document':src_doc,
                    'confidence':'unresolved','notes_on_ambiguity':[reason]})
                ambiguous_codes.append({'canonical_key':key,'manufacturer_tone_code':code,
                    'ambiguity_reason':'no_printed_legend_and_no_safe_inference','details':reason})
                unresolved.append({'canonical_key':key,'manufacturer_tone_code':code,
                    'reason':'tone_meaning_unresolved','details':reason})
                continue
            status, term, tones, why = dec
            conf = 'high' if status == 'confirmed' else 'medium'
            flag = status != 'confirmed'
            tone_reference.append({'canonical_key':key,'brand':brand,'product_line':line,
                'manufacturer_tone_code':code,'manufacturer_term':term,
                'manufacturer_definition':why,
                'evidence_source_url':src_url,'evidence_source_document':src_doc,
                'confidence':conf,'notes_on_ambiguity':([] if not flag else [why])})
            if flag and ('ambiguous' in (term or '') or code in ('M','MM','B')):
                ambiguous_codes.append({'canonical_key':key,'manufacturer_tone_code':code,
                    'ambiguity_reason':'letter_convention_inferred','details':why})
            norm_map.append({'canonical_key':key,'brand':brand,'product_line':line,
                'manufacturer_tone_code':code,'manufacturer_term':term,
                'normalized_tones':tones,'mapping_rationale':why,
                'mapping_confidence':conf,'ambiguity_flag':flag,'notes':[]})

assert all(set(m['normalized_tones']) <= TAXONOMY for m in norm_map)

json.dump({'stage':6,'artifact':'manufacturer_tone_reference','batch':2,
           'completion_status':'complete',
           'manufacturer_tone_reference':tone_reference,
           'ambiguous_tone_codes':ambiguous_codes,
           'issue_log':[
             {'item':'Matrix letter codes','issue_type':'legend_gap',
              'details':'The 2023 manual prints a DIGIT tone legend and decodes example letter codes but no complete letter table; letter meanings beyond the printed examples are inferred and flagged.'},
             {'item':'Majirel/Dia Light digit 1 and 5','issue_type':'taxonomy_translation',
              'details':"Printed legend words are 'blue' and 'red-violet'; Ash/Mahogany added as conventional family names with the interpretation noted in rationales."}]},
          open(os.path.join(B2,'tone_reference_stage6.json'),'w'), indent=2, ensure_ascii=False)

json.dump({'stage':7,'artifact':'tone_normalization_map','batch':2,
           'completion_status':'complete',
           'tone_normalization_map':norm_map,'unresolved_mappings':unresolved,
           'issue_log':[]},
          open(os.path.join(B2,'tone_normalization_map_stage7.json'),'w'), indent=2, ensure_ascii=False)

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
    normalized.append({
        'canonical_key':key,'brand':r['brand'],'product_line':r['product_line'],
        'shade_code':r['shade_code'],'shade_name':r['shade_name'],'level':r['level'],
        'manufacturer_tone_codes':r['manufacturer_tone_codes'],
        'manufacturer_tone_descriptions':r['manufacturer_tone_descriptions'],
        'normalized_tones':tones,'color_type':r.get('color_type') or tech.get('color_type'),
        'gray_coverage_claim':r.get('gray_coverage_claim'),
        'lift_levels':r.get('lift_capability'),
        'mixing_ratio':mixing,'developer_options':devs,
        'processing_time_minutes':r.get('processing_time_minutes'),
        'special_usage_notes':r.get('special_usage_notes'),
        'official_swatch_image_exists':r.get('official_swatch_image_exists'),
        'region_or_market':r.get('region_or_market'),
        'discontinued_status':tech.get('discontinued_status'),
        'source_url':r['source_url'],'source_document':r['source_document'],
        'source_type':r['source_type'],'source_publication_date':r.get('source_publication_date'),
        'source_confidence':r['source_confidence'],'evidence_status':r['evidence_status'],
        'assumptions':assumptions,'data_gaps':gaps})
    if not r['manufacturer_tone_codes'] and 'clear' not in str(r['shade_code']).lower():
        merge_issues.append({'canonical_key':key,'shade_code':r['shade_code'],
            'issue_type':'no_tone_codes','details':'Raw record carries no manufacturer tone codes; normalized_tones left empty.'})

json.dump({'stage':8,'artifact':'normalized_shade_records','batch':2,
           'completion_status':'complete',
           'normalized_shade_records':normalized,'merge_issues':merge_issues,
           'issue_log':[]},
          open(os.path.join(B2,'normalized_shade_records_stage8.json'),'w'), indent=2, ensure_ascii=False)

findings = []
seen = defaultdict(list)
for n in normalized: seen[(n['canonical_key'], n['shade_code'])].append(n)
for (key, code), rows in seen.items():
    if len(rows) > 1:
        findings.append({'canonical_key':key,'record_ref':code,'issue_type':'duplicate_shade_code',
            'severity':'high','details':f'{len(rows)} normalized records share shade_code {code}',
            'recommended_fix':'Distinguish sub-range variants explicitly or deduplicate.'})
for n in normalized:
    ref = f"{n['canonical_key']}#{n['shade_code']}"
    if not n['source_url']:
        findings.append({'canonical_key':n['canonical_key'],'record_ref':ref,
            'issue_type':'missing_provenance','severity':'high','details':'source_url empty',
            'recommended_fix':'Re-extract with source captured.'})
    if n['manufacturer_tone_codes'] and not n['normalized_tones']:
        findings.append({'canonical_key':n['canonical_key'],'record_ref':ref,
            'issue_type':'unmapped_tone_codes','severity':'medium',
            'details':f"codes {n['manufacturer_tone_codes']} have no normalized mapping",
            'recommended_fix':'Resolve via official legend retrieval.'})
per_line = defaultdict(int)
for n in normalized: per_line[n['canonical_key']] += 1
json.dump({'stage':9,'artifact':'qa_findings','batch':2,'completion_status':'complete',
           'qa_findings':findings,'corrected_records_recommendations':[],
           'unresolved_issues':unresolved,'issue_log':[],
           'record_counts_by_line':dict(per_line)},
          open(os.path.join(B2,'qa_findings_stage9.json'),'w'), indent=2, ensure_ascii=False)

print('stage6:', len(tone_reference), '| ambiguous:', len(ambiguous_codes))
print('stage7:', len(norm_map), '| unresolved:', len(unresolved))
print('stage8:', len(normalized), '| merge issues:', len(merge_issues))
print('stage9 findings:', len(findings))
for f_ in findings[:20]:
    print('  -', f_['issue_type'], f_['record_ref'], '|', f_['details'][:100])
