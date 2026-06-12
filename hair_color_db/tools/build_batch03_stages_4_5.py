#!/usr/bin/env python3
"""Batch 3 Stage 4-5: Pravana shade extraction + Goldwell line technical."""
import json, re, time, os
import requests
from html import unescape

BASE = os.path.join(os.path.dirname(__file__), '..')
OUT = os.path.join(BASE, 'batches', 'batch03')
os.makedirs(OUT, exist_ok=True)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

SELECTED_PRAVANA = {
    'Pravana::ChromaSilk Creme Color::US',
    'Pravana::ChromaSilk Express Tones::US',
    'Pravana::ChromaSilk VIVIDS::US',
}

LINE_PAGES = {
    'chromasilk-express-tones', 'chromasilk-vivids-original',
    'chromasilk-vivids-neons', 'chromasilk-vivids-pastels',
    'chromasilk-creme-color-ash', 'chromasilk-creme-color-beige',
    'chromasilk-creme-color-copper', 'chromasilk-creme-color-gold',
    'chromasilk-creme-color-mahogany', 'chromasilk-creme-color-natural',
    'chromasilk-creme-color-neutral', 'chromasilk-creme-color-red',
    'chromasilk-creme-color-violet', 'chromasilk-creme-color-warm',
    'chromasilk-hydragloss', 'chromasilk-vivids-everlasting',
}


def strip_html(s):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def parse_jsonld(text):
    products = []
    for block in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', text, re.I | re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        graphs = data.get('@graph', [data]) if isinstance(data, dict) else data
        if not isinstance(graphs, list):
            graphs = [graphs]
        for node in graphs:
            if isinstance(node, dict) and node.get('@type') == 'Product':
                products.append(node)
    return products


def props_to_dict(product):
    return {p.get('name', ''): p.get('value', '') for p in (product.get('additionalProperty') or []) if isinstance(p, dict)}


def parse_numeric_code(slug):
    parts = slug.split('-')
    if len(parts) >= 2 and parts[0].isdigit():
        if parts[1].isdigit():
            code = f"{parts[0]}.{parts[1]}"
            if len(parts) >= 3 and parts[2].isdigit():
                code = f"{parts[0]}.{parts[1]}{parts[2]}"
            return code
        if re.match(r'^[0-9]+[a-zA-Z]+$', parts[0] + parts[1]):
            return (parts[0] + parts[1]).upper()
    return None


def slug_to_display_code(slug):
    """Manufacturer-facing code for non-numeric lines: slug words title-cased."""
    if slug in LINE_PAGES:
        return None
    num = parse_numeric_code(slug)
    if num:
        return num
    return slug.replace('-', ' ').title()


def tone_codes_from_shade_code(code):
    """Keep the full post-decimal reflect segment as one manufacturer code (e.g. 9.12 -> '12')."""
    if not code or '.' not in str(code):
        return []
    return [str(code).split('.', 1)[1]]


def classify_line(url):
    if '/chromasilk-express-tones/' in url:
        return 'Pravana::ChromaSilk Express Tones::US', 'ChromaSilk Express Tones', 'demi-permanent toner'
    if '/chromasilk-vivids-' in url:
        return 'Pravana::ChromaSilk VIVIDS::US', 'ChromaSilk VIVIDS', 'semi-permanent direct dye'
    if '/permanent/chromasilk-creme-color' in url or '/chromasilk-creme-color-' in url:
        return 'Pravana::ChromaSilk Creme Color::US', 'ChromaSilk Crème Color (Permanent)', 'permanent'
    return None, None, None


def is_shade_page(url, slug):
    if slug in LINE_PAGES:
        return False
    key, _, _ = classify_line(url)
    if not key or key not in SELECTED_PRAVANA:
        return False
    if key == 'Pravana::ChromaSilk Creme Color::US':
        return parse_numeric_code(slug) is not None
    return True


def discover_shade_urls():
    r = session.get('https://www.pravana.com/products/color/', timeout=30)
    urls = sorted(set(re.findall(r'href="(https://www\.pravana\.com/products/color/[^"]+)"', r.text)))
    out = []
    for u in urls:
        slug = u.rstrip('/').split('/')[-1]
        if u.count('/') >= 7 and is_shade_page(u, slug):
            out.append(u)
    return out


def extract_shade(url):
    slug = url.rstrip('/').split('/')[-1]
    key, line_name, color_type = classify_line(url)
    resp = session.get(url, timeout=25)
    resp.raise_for_status()
    products = parse_jsonld(resp.text)
    product = products[0] if products else {}
    props = props_to_dict(product)
    shade_code = parse_numeric_code(slug) or slug_to_display_code(slug)
    product_name = product.get('name', '')
    if product_name:
        product_name = unescape(product_name.replace('&#8211;', '–'))
    shade_name = product_name if product_name and product_name not in ('Violet', 'Blue', 'Red') or key != 'Pravana::ChromaSilk Creme Color::US' else product_name
    # For creme color, prefer full printed name from product JSON-LD (e.g. "7.1 Ash Blonde")
    if key == 'Pravana::ChromaSilk Creme Color::US' and product_name:
        shade_name = product_name
    desc = product.get('description') or ''
    meta = re.search(r'<meta name="description" content="([^"]*)"', resp.text)
    if meta and not desc:
        desc = meta.group(1)
    level = int(re.match(r'^(\d+)', str(shade_code)).group(1)) if shade_code and re.match(r'^(\d+)', str(shade_code)) else None
    tone_codes = tone_codes_from_shade_code(shade_code)
    how_to = props.get('How To Use', '')
    features = props.get('Features', '')
    family = props.get('Family', '') or props.get('Tone Family', '')
    tone_desc = [x for x in [desc, f"Family: {family}" if family else ''] if x]
    mixing = None
    m = re.search(r'(1:\d+(?:\.\d+)?(?:½|/2)?)', how_to)
    if m:
        mixing = m.group(1).replace('½', '.5')
    proc = None
    for pat in [r'Process(?: for)?\s+(\d+)\s+minutes?', r'(\d+)\s+minutes?\s+or\s+less']:
        m2 = re.search(pat, how_to, re.I)
        if m2:
            proc = int(m2.group(1))
            break
    devs = []
    if 'Zero Lift Creme Developer' in how_to:
        devs.append('ChromaSilk Zero Lift Creme Developer')
    if re.search(r'creme developer\s+10-40V', how_to, re.I):
        devs.append('ChromaSilk Creme Developer 10V–40V')
    gray = features if re.search(r'gr[ae]y', features, re.I) else None
    family_path = url.split('/products/color/')[1].rsplit('/', 1)[0] if '/products/color/' in url else None
    gaps = []
    if product.get('sku') and str(shade_code) != str(product.get('sku')):
        gaps.append(f"Internal SKU {product['sku']} recorded separately; shade_code uses manufacturer-facing code from URL/name, not SKU.")
    if family_path and 'creme-color-' in family_path:
        gaps.append(f"tonal_family_path={family_path.split('/')[-1]}")
    return {
        'canonical_key': key,
        'brand': 'Pravana',
        'product_line': line_name,
        'shade_code': shade_code,
        'shade_name': shade_name,
        'level': level,
        'manufacturer_tone_codes': tone_codes,
        'manufacturer_tone_descriptions': tone_desc,
        'color_type': color_type,
        'gray_coverage_claim': gray,
        'lift_capability': None,
        'mixing_ratio': mixing,
        'developer_recommendations': devs,
        'processing_time_minutes': proc,
        'special_usage_notes': how_to or None,
        'official_swatch_image_exists': bool(product.get('image')),
        'region_or_market': 'US',
        'source_url': url,
        'source_document': f'PRAVANA official product page ({slug})',
        'source_type': 'official_product_page',
        'source_publication_date': None,
        'source_confidence': 'high',
        'evidence_status': 'confirmed' if product else 'partially_confirmed',
        'assumptions': ([] if product else ['JSON-LD Product block missing; fields parsed from HTML/meta only']),
        'data_gaps': gaps,
    }


def build_line_technical():
    records = []
    records.append({
        'canonical_key': 'Pravana::ChromaSilk Creme Color::US',
        'brand': 'Pravana', 'product_line': 'ChromaSilk Crème Color (Permanent)',
        'color_type': 'permanent',
        'default_mixing_ratio': '1:1.5 (1 part ChromaSilk Creme Color : 1.5 parts ChromaSilk Creme Developer)',
        'developer_options': ['ChromaSilk Creme Developer 10V', 'ChromaSilk Creme Developer 20V', 'ChromaSilk Creme Developer 30V', 'ChromaSilk Creme Developer 40V'],
        'developer_strengths_if_stated': '10V–40V per official product pages ("creme developer 10-40V")',
        'processing_time_ranges': '30 minutes — up to 45 minutes (printed on product pages)',
        'gray_coverage_rules': 'Up to 100% gray coverage (printed Features on product pages)',
        'lift_rules': None,
        'tone_family_legend': '12 tonal families; per-family descriptions on product pages (e.g., Ash Family: cool green base)',
        'special_usage_notes': '3 oz tube; 1:1.5 mixing ratio yields 7.5 oz working product (printed on product pages)',
        'region_or_market': 'US', 'discontinued_status': None,
        'source_url': 'https://www.pravana.com/pro/mixing-ratio/',
        'source_document': 'PRAVANA Mixing Ratio Guide (official page)',
        'source_confidence': 'high', 'evidence_status': 'confirmed',
        'assumptions': ['Developer volume by desired result not on mixing-ratio landing page.'],
        'data_gaps': ['Full digit tone legend in pro-gated Product Knowledge Guide PDF; family descriptions used from public product pages.']
    })
    records.append({
        'canonical_key': 'Pravana::ChromaSilk Express Tones::US',
        'brand': 'Pravana', 'product_line': 'ChromaSilk Express Tones',
        'color_type': 'demi-permanent toner',
        'default_mixing_ratio': '1:1.5 (1 part Express Tones : 1.5 parts ChromaSilk Zero Lift Creme Developer)',
        'developer_options': ['ChromaSilk Zero Lift Creme Developer'],
        'developer_strengths_if_stated': 'Zero Lift only (printed on product pages)',
        'processing_time_ranges': '5 minutes or less (printed on product pages)',
        'gray_coverage_rules': None, 'lift_rules': 'No lift — ammonia-free toners',
        'tone_family_legend': 'Blondes and Brunettes series; bases stated per shade (e.g., Ash: cool/green base)',
        'special_usage_notes': 'Apply to damp hair; Express Tones Clear may be added (Ash product page)',
        'region_or_market': 'US', 'discontinued_status': None,
        'source_url': 'https://www.pravana.com/products/color/demi-permanent/chromasilk-express-tones/ash/',
        'source_document': 'ChromaSilk Express Tones Ash product page',
        'source_confidence': 'high', 'evidence_status': 'confirmed',
        'assumptions': ['Line-level rules from representative Express Tones pages applied per collection.'],
        'data_gaps': []
    })
    records.append({
        'canonical_key': 'Pravana::ChromaSilk VIVIDS::US',
        'brand': 'Pravana', 'product_line': 'ChromaSilk VIVIDS (Original, Neons, Pastels)',
        'color_type': 'semi-permanent direct dye',
        'default_mixing_ratio': None, 'developer_options': [],
        'developer_strengths_if_stated': None,
        'processing_time_ranges': '20–30 minutes on several shade pages; not uniform across collection',
        'gray_coverage_rules': 'N/A — non-oxidative, no developer',
        'lift_rules': 'No lift; pre-lightening required for vivid deposit on natural hair',
        'tone_family_legend': 'Named direct dyes (no level/tone digit system)',
        'special_usage_notes': 'No developer; intermixable across VIVIDS shades',
        'region_or_market': 'US', 'discontinued_status': None,
        'source_url': 'https://www.pravana.com/products/color/semi-permanent/chromasilk-vivids-original/',
        'source_document': 'ChromaSilk VIVIDS Original line page',
        'source_confidence': 'high', 'evidence_status': 'confirmed',
        'assumptions': ['Original, Neons, Pastels grouped under canonical VIVIDS line per Stage 1 inventory.'],
        'data_gaps': ['Processing time varies by shade page.']
    })
    for key, url, line, ctype, mixing in [
        ('Goldwell::Topchic::US', 'https://www.goldwell.com/en-us/education/color-guide1/topchic/', 'Topchic', 'permanent', '1:1 color:TOPCHIC Cream Developer Lotion'),
        ('Goldwell::Colorance::US', 'https://www.goldwell.com/en-us/education/color-guide1/colorance/', 'Colorance (incl. Cover Plus, Gloss Tones)', 'demi-permanent', 'See gray-coverage table (Colorance Lotion + Fashion/N-Shade)'),
    ]:
        records.append({
            'canonical_key': key, 'brand': 'Goldwell', 'product_line': line, 'color_type': ctype,
            'default_mixing_ratio': mixing,
            'developer_options': (['TOPCHIC Cream Developer Lotion 3% (10 vol.)', '6% (20 vol.)', '9% (30 vol.)', '12% (40 vol.)']
                                  if 'Topchic' in line else ['Colorance Lotion']),
            'developer_strengths_if_stated': ('Virgin-hair deposit/lift table on Color Guide' if 'Topchic' in line else 'Colorance Lotion only'),
            'processing_time_ranges': None,
            'gray_coverage_rules': ('N-/NA-/NN- vs Fashion shade mixing by % white (printed table)'
                                    if 'Topchic' in line else 'Fashion + N-shade by % white (printed table)'),
            'lift_rules': ('Up to 3 levels virgin hair with 12% (40 vol.)' if 'Topchic' in line else 'Deposit only'),
            'tone_family_legend': None,
            'special_usage_notes': 'Shade palettes are JPEG swatch charts on Color Guide; codes not extractable as text.',
            'region_or_market': 'US', 'discontinued_status': None,
            'source_url': url, 'source_document': f'Goldwell US Color Guide — {line} section',
            'source_confidence': 'high', 'evidence_status': 'confirmed',
            'assumptions': [], 'data_gaps': ['Shade-level extraction blocked: image-only palettes on official Color Guide (no PDF/text chart cataloged).']
        })
    return records


def main():
    urls = discover_shade_urls()
    raw, errors = [], []
    for i, url in enumerate(urls):
        try:
            raw.append(extract_shade(url))
        except Exception as e:
            errors.append({'url': url, 'error': str(e)})
        if i % 20 == 0:
            time.sleep(0.25)
    line_tech = build_line_technical()
    json.dump({'stage': 4, 'batch': 3, 'artifact': 'raw_shade_records', 'completion_status': 'complete',
               'raw_shade_records': raw, 'fetch_errors': errors,
               'records_by_line': {k: sum(1 for r in raw if r['canonical_key'] == k) for k in SELECTED_PRAVANA}},
              open(os.path.join(OUT, 'pravana_raw_shade_records.json'), 'w'), indent=2, ensure_ascii=False)
    json.dump({'stage': 5, 'batch': 3, 'artifact': 'line_technical_records', 'completion_status': 'complete',
               'line_technical_records': [t for t in line_tech if t['brand'] == 'Pravana']},
              open(os.path.join(OUT, 'pravana_line_technical_records.json'), 'w'), indent=2, ensure_ascii=False)
    json.dump({'stage': 5, 'batch': 3, 'artifact': 'line_technical_records', 'completion_status': 'partial',
               'line_technical_records': [t for t in line_tech if t['brand'] == 'Goldwell']},
              open(os.path.join(OUT, 'goldwell_line_technical_records.json'), 'w'), indent=2, ensure_ascii=False)
    print('raw', len(raw), 'errors', len(errors))
    for k in SELECTED_PRAVANA:
        print(' ', k, sum(1 for r in raw if r['canonical_key'] == k))


if __name__ == '__main__':
    main()
