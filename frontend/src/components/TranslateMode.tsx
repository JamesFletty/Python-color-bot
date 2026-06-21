import { useState } from "react";
import { ChevronDown, ArrowRightLeft } from "lucide-react";
import type { Brand, Line, AIFormulaResponse } from "../api";
import { aiTranslate } from "../api";

interface Props {
  brands: Brand[];
  onResult: (r: AIFormulaResponse) => void;
  onLoading: (v: boolean) => void;
  onError: (e: string | null) => void;
}

export default function TranslateMode({ brands, onResult, onLoading, onError }: Props) {
  const [sourceFormula, setSourceFormula] = useState("");
  const [sourceLine, setSourceLine] = useState("");
  const [targetBrandId, setTargetBrandId] = useState<string | null>(null);
  const [targetLine, setTargetLine] = useState<Line | null>(null);

  const targetBrand = brands.find((b) => b.id === targetBrandId) ?? null;

  function handleTargetBrandChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    setTargetBrandId(id || null);
    setTargetLine(null);
  }

  function handleTargetLineChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    const line = targetBrand?.lines.find((l) => l.id === id) ?? null;
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
      const result = await aiTranslate({
        source_formula: sourceFormula,
        source_line: sourceLine.trim() || undefined,
        target_line: targetLine.name,
        target_line_id: targetLine.id,
        target_canonical_key: targetLine.key,
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
      {/* Source formula */}
      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Source Formula
        </label>
        <textarea
          value={sourceFormula}
          onChange={(e) => setSourceFormula(e.target.value)}
          placeholder={
            "Paste or type the formula to translate…\n\nExamples:\n• Redken Color Gels 7NW + 7NA 1:1, 20 vol developer\n• Wella Koleston 7/3 + 7/0, 40ml each, 9% developer\n• IGORA ROYAL 6-1 + 6-0, 1:1.5, 30 vol"
          }
          rows={6}
          className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm text-[var(--text)] placeholder-[var(--muted)]/60 focus:outline-none focus:border-[var(--amber)]/50 transition-colors resize-none leading-relaxed"
        />
      </div>

      {/* Source line (optional) */}
      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Source Brand / Line{" "}
          <span className="normal-case font-normal opacity-60">(optional if in formula)</span>
        </label>
        <input
          type="text"
          value={sourceLine}
          onChange={(e) => setSourceLine(e.target.value)}
          placeholder="e.g. Redken Color Gels Lacquers…"
          className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] placeholder-[var(--muted)] focus:outline-none focus:border-[var(--amber)]/50 transition-colors"
        />
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-[var(--border)]" />
        <ArrowRightLeft size={14} className="text-[var(--amber)] shrink-0" />
        <div className="flex-1 h-px bg-[var(--border)]" />
      </div>

      {/* Target brand */}
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
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
        </div>
      </div>

      {/* Target line */}
      {targetBrand && (
        <div>
          <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
            Target Line
          </label>
          <div className="relative">
            <select
              value={targetLine?.id ?? ""}
              onChange={handleTargetLineChange}
              className="w-full appearance-none bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--amber)]/50 transition-colors cursor-pointer"
            >
              <option value="">Select line…</option>
              {targetBrand.lines.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                  {l.color_type ? ` (${l.color_type})` : ""}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
          </div>
        </div>
      )}

      {/* Selected target summary */}
      {targetLine && (
        <div className="px-3 py-2 bg-[var(--amber-dim)] border border-[var(--amber)]/20 rounded-lg">
          <span className="text-xs text-[var(--amber)] mono">→ </span>
          <span className="text-xs text-[var(--text)]">
            {targetBrand?.name} · {targetLine.name}
          </span>
          {targetLine.color_type && (
            <span className="text-xs text-[var(--muted)] ml-2">({targetLine.color_type})</span>
          )}
        </div>
      )}

      {/* Submit */}
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
