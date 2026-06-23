import { useState } from "react";
import { ChevronDown, ArrowRightLeft } from "lucide-react";
import type { Brand, Line, FormulaResult } from "../api";
import { translateFormula } from "../api";

interface Props {
  brands: Brand[];
  onResult: (r: FormulaResult) => void;
  onLoading: (v: boolean) => void;
  onError: (e: string | null) => void;
}

export default function TranslateMode({ brands, onResult, onLoading, onError }: Props) {
  const [sourceFormula, setSourceFormula] = useState("");
  const [sourceLine, setSourceLine] = useState("");
  const [targetBrandId, setTargetBrandId] = useState<number | null>(null);
  const [targetLine, setTargetLine] = useState<Line | null>(null);

  const targetBrand = brands.find((b) => b.brand_id === targetBrandId) ?? null;

  function handleTargetBrandChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value ? Number(e.target.value) : null;
    setTargetBrandId(id);
    setTargetLine(null);
  }

  function handleTargetLineChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = Number(e.target.value);
    const line = targetBrand?.lines.find((l) => l.line_id === id) ?? null;
    setTargetLine(line);
  }

  async function handleSubmit() {
    if (!targetLine) {
      onError("Please select a target color line.");
      return;
    }
    if (!sourceFormula.trim()) {
      onError("Please enter the formula to translate.");
      return;
    }
    onError(null);
    onLoading(true);
    try {
      const result = await translateFormula({
        source_formula: sourceFormula,
        source_line: sourceLine.trim() || undefined,
        target_line: targetLine.line_name,
        target_line_id: targetLine.line_id,
        target_canonical_key: targetLine.canonical_key,
      });
      onResult(result);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      onLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Source Formula
        </label>
        <textarea
          value={sourceFormula}
          onChange={(e) => setSourceFormula(e.target.value)}
          placeholder="Paste or type the formula to translate…"
          rows={6}
          className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm text-[var(--text)] placeholder-[var(--muted)]/60 focus:outline-none focus:border-[var(--amber)]/50 transition-colors resize-none leading-relaxed"
        />
      </div>

      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Source Brand / Line{" "}
          <span className="normal-case font-normal opacity-60">(optional)</span>
        </label>
        <input
          type="text"
          value={sourceLine}
          onChange={(e) => setSourceLine(e.target.value)}
          placeholder="e.g. Redken Color Gels Lacquers…"
          className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] placeholder-[var(--muted)] focus:outline-none focus:border-[var(--amber)]/50 transition-colors"
        />
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-[var(--border)]" />
        <ArrowRightLeft size={14} className="text-[var(--amber)] shrink-0" />
        <div className="flex-1 h-px bg-[var(--border)]" />
      </div>

      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Target Brand
        </label>
        <div className="relative">
          <select
            value={targetBrandId ?? ""}
            onChange={handleTargetBrandChange}
            className="w-full appearance-none bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--amber)]/50 transition-colors cursor-pointer"
          >
            <option value="">Select target brand…</option>
            {brands.map((b) => (
              <option key={b.brand_id} value={b.brand_id}>
                {b.brand_name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
        </div>
      </div>

      {targetBrand && (
        <div>
          <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
            Target Line
          </label>
          <div className="relative">
            <select
              value={targetLine?.line_id ?? ""}
              onChange={handleTargetLineChange}
              className="w-full appearance-none bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--amber)]/50 transition-colors cursor-pointer"
            >
              <option value="">Select line…</option>
              {targetBrand.lines.map((l) => (
                <option key={l.line_id} value={l.line_id}>
                  {l.line_name}
                  {l.color_type ? ` (${l.color_type})` : ""}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
          </div>
        </div>
      )}

      {targetLine && (
        <div className="px-3 py-2 bg-[var(--amber-dim)] border border-[var(--amber)]/20 rounded-lg">
          <span className="text-xs text-[var(--amber)] mono">→ </span>
          <span className="text-xs text-[var(--text)]">
            {targetBrand?.brand_name} · {targetLine.line_name}
          </span>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!targetLine || !sourceFormula.trim()}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm transition-all
          bg-[var(--amber)] text-black hover:brightness-110 active:scale-[0.99]
          disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:brightness-100"
      >
        <ArrowRightLeft size={15} />
        Translate Formula
      </button>
    </div>
  );
}
