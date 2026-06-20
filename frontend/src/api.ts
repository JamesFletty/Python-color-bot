export interface Brand {
  id: number;
  name: string;
  lines: Line[];
}

export interface Line {
  id: number;
  name: string;
  key: string;
  color_type: string | null;
}

export interface Shade {
  id: number;
  code: string;
  name: string | null;
  level: number | null;
  color_type: string | null;
  sub_range: string | null;
  mixing_ratio: string | null;
  line: string;
  brand: string;
}

export interface AIFormulaResponse {
  formula: Record<string, unknown>;
  ai_explanation: string;
  structured_request: Record<string, unknown>;
  translation_notes?: string;
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
  return req("/api/brands");
}

export function fetchShades(lineId: number, query?: string): Promise<Shade[]> {
  const q = query ? `&q=${encodeURIComponent(query)}` : "";
  return req(`/api/shades?line_id=${lineId}${q}`);
}

export function aiFormula(payload: {
  user_input: string;
  color_line: string;
  line_id: number;
  canonical_key: string;
}): Promise<AIFormulaResponse> {
  return req("/api/ai/formula", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function aiTranslate(payload: {
  source_formula: string;
  source_line?: string;
  target_line: string;
  target_line_id: number;
  target_canonical_key: string;
}): Promise<AIFormulaResponse> {
  return req("/api/ai/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
