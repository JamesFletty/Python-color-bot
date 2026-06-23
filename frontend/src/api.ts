/** v2 API types and client (ColorSynth Formula Engine). */

export interface Line {
  line_id: number;
  line_name: string;
  canonical_key: string;
  color_type: string | null;
  region_or_market?: string | null;
}

export interface Brand {
  brand_id: number;
  brand_name: string;
  lines: Line[];
}

export interface Shade {
  shade_id: number;
  shade_code: string;
  shade_name: string | null;
  level: number | null;
  normalized_tones: string[];
  sub_range: string | null;
  color_type: string | null;
}

export interface FormulaResponse {
  status: "ok" | "caution" | "blocked" | "error";
  shade: {
    shade_id: number;
    shade_code: string;
    shade_name: string | null;
    level: number | null;
    brand: string;
    product_line: string;
    canonical_key: string;
    normalized_tones: string[];
    sub_range: string | null;
  };
  formula: {
    developer: string;
    developer_rationale: string | null;
    mixing_ratio: string;
    processing_time: string;
    gray_coverage_guidance: string | null;
    fill_pigment_guidance: Record<string, unknown> | null;
  };
  hair_conditions: {
    natural_level: number | null;
    desired_level: number | null;
    gray_percent: number;
    porosity: number;
    elasticity: number;
    texture: string;
  };
  warnings: string[];
  assumptions: string[];
  matched_rules: string[];
}

export interface ParsedRequest {
  shade: string;
  current_level: number | null;
  desired_level: number | null;
  gray_percent: number;
  porosity: number;
  elasticity: number;
  texture: "fine" | "medium" | "coarse";
  service_intent: string;
  line: string | null;
  translation_notes: string | null;
  parse_source: "llm" | "deterministic";
}

/** Unified result shape consumed by ResultPanel. */
export interface FormulaResult {
  formula: FormulaResponse;
  ai_explanation: string;
  structured_request: Record<string, unknown>;
  translation_notes?: string;
  parse_source?: string;
  status: string;
}

const BASE = "";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function fetchBrands(): Promise<Brand[]> {
  return req("/brands");
}

export function fetchShades(lineId: number, query?: string): Promise<Shade[]> {
  const params = new URLSearchParams({ limit: "40" });
  if (query) params.set("q", query);
  return req(`/lines/${lineId}/shades?${params}`);
}

export function aiParse(payload: {
  user_input: string;
  color_line: string;
  line_id: number;
  canonical_key: string;
}): Promise<ParsedRequest> {
  return req("/ai/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function buildFormula(payload: {
  shade: string;
  line_hint?: string;
  current_level?: number | null;
  desired_level?: number | null;
  gray_percent?: number;
  porosity?: number;
  elasticity?: number;
  texture?: string;
  service_intent?: string;
}): Promise<FormulaResponse> {
  return req("/formula", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function aiExplain(payload: {
  formula_result: FormulaResponse;
  user_input: string;
  color_line: string;
  mode?: "formula" | "translate";
  translation_notes?: string;
}): Promise<{ summary: string }> {
  return req("/ai/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      formula_result: payload.formula_result,
      user_input: payload.user_input,
      color_line: payload.color_line,
      mode: payload.mode ?? "formula",
      translation_notes: payload.translation_notes,
    }),
  });
}

function fallbackExplanation(formula: FormulaResponse): string {
  const { shade, formula: block, warnings } = formula;
  const parts = [
    `${shade.brand} ${shade.product_line} ${shade.shade_code}`,
    `${block.developer} developer`,
    `${block.mixing_ratio} mix`,
    `${block.processing_time} processing`,
  ];
  if (warnings.length) parts.push(`Note: ${warnings.join("; ")}`);
  return parts.filter(Boolean).join(". ") + ".";
}

export async function computeFormula(payload: {
  user_input: string;
  color_line: string;
  line_id: number;
  canonical_key: string;
}): Promise<FormulaResult> {
  const parsed = await aiParse(payload);
  const formula = await buildFormula({
    shade: parsed.shade,
    line_hint: parsed.line ?? payload.color_line,
    current_level: parsed.current_level,
    desired_level: parsed.desired_level,
    gray_percent: parsed.gray_percent,
    porosity: parsed.porosity,
    elasticity: parsed.elasticity,
    texture: parsed.texture,
    service_intent: parsed.service_intent,
  });

  let ai_explanation = fallbackExplanation(formula);
  try {
    const explained = await aiExplain({
      formula_result: formula,
      user_input: payload.user_input,
      color_line: payload.color_line,
      mode: "formula",
    });
    ai_explanation = explained.summary;
  } catch {
    // LLM optional — deterministic explanation above
  }

  return {
    formula,
    ai_explanation,
    structured_request: parsed as unknown as Record<string, unknown>,
    parse_source: parsed.parse_source,
    status: formula.status,
  };
}

export async function translateFormula(payload: {
  source_formula: string;
  source_line?: string;
  source_canonical_key?: string;
  target_line: string;
  target_line_id: number;
  target_canonical_key: string;
}): Promise<FormulaResult> {
  const translated = await req<
    FormulaResponse & {
      structured_request: Record<string, unknown>;
      translation_notes?: string;
      parse_source?: string;
    }
  >("/ai/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const { structured_request, translation_notes, parse_source, ...formula } = translated;

  let ai_explanation = fallbackExplanation(formula);
  try {
    const explained = await aiExplain({
      formula_result: formula,
      user_input: payload.source_formula,
      color_line: payload.target_line,
      mode: "translate",
      translation_notes: translation_notes ?? undefined,
    });
    ai_explanation = explained.summary;
  } catch {
    // LLM optional
  }

  return {
    formula,
    ai_explanation,
    structured_request: structured_request ?? {},
    translation_notes,
    parse_source,
    status: formula.status,
  };
}
