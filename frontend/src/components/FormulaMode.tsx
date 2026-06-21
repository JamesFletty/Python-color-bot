import { useState } from "react";
import { ChevronDown, Search, Wand2 } from "lucide-react";
import type { Brand, Line, AIFormulaResponse } from "../api";
import { aiFormula, fetchShades } from "../api";
import type { Shade } from "../api";

interface Props {
  brands: Brand[];
  onResult: (r: AIFormulaResponse) => void;
  onLoading: (v: boolean) => void;
  onError: (e: string | null) => void;
}

export default function FormulaMode({ brands, onResult, onLoading, onError }: Props) {
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);
  const [selectedLine, setSelectedLine] = useState<Line | null>(null);
  const [userInput, setUserInput] = useState("");
  const [shadeQuery, setShadeQuery] = useState("");
  const [shades, setShades] = useState<Shade[]>([]);
  const [shadesLoading, setShadesLoading] = useState(false);
  const [selectedShade, setSelectedShade] = useState<Shade | null>(null);

  const selectedBrand = brands.find((b) => b.id === selectedBrandId) ?? null;

  function handleBrandChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    setSelectedBrandId(id || null);
    setSelectedLine(null);
    setShades([]);
    setSelectedShade(null);
  }

  function handleLineChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value;
    const line = selectedBrand?.lines.find((l) => l.id === id) ?? null;
    setSelectedLine(line);
    setShades([]);
    setSelectedShade(null);
  }

  async function handleShadeSearch() {
    if (!selectedLine) return;
    setShadesLoading(true);
    try {
      const results = await fetchShades(selectedLine.id, shadeQuery || undefined);
      setShades(results);
    } catch {
      // ignore shade search errors silently
    } finally {
      setShadesLoading(false);
    }
  }

  async function handleSubmit() {
    if (!selectedLine) {
      onError("Please select a color line first.");
      return;
    }
    if (!userInput.trim()) {
      onError("Please describe the client and desired result.");
      return;
    }
    onError(null);
    onLoading(true);
    try {
      const shadeHint = selectedShade ? ` (shade code: ${selectedShade.code})` : "";
      const result = await aiFormula({
        user_input: userInput + shadeHint,
        color_line: selectedLine.name,
        line_id: selectedLine.id,
        canonical_key: selectedLine.key,
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
      {/* Brand selector */}
      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Brand
        </label>
        <div className="relative">
          <select
            value={selectedBrandId ?? ""}
            onChange={handleBrandChange}
            className="w-full appearance-none bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--teal)]/50 transition-colors cursor-pointer"
          >
            <option value="">Select brand…</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
        </div>
      </div>

      {/* Line selector */}
      {selectedBrand && (
        <div>
          <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
            Product Line
          </label>
          <div className="relative">
            <select
              value={selectedLine?.id ?? ""}
              onChange={handleLineChange}
              className="w-full appearance-none bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] focus:outline-none focus:border-[var(--teal)]/50 transition-colors cursor-pointer"
            >
              <option value="">Select line…</option>
              {selectedBrand.lines.map((l) => (
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

      {/* Shade search (optional) */}
      {selectedLine && (
        <div>
          <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
            Shade Reference{" "}
            <span className="normal-case font-normal opacity-60">(optional — type level or name)</span>
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={shadeQuery}
              onChange={(e) => setShadeQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleShadeSearch()}
              placeholder="e.g. 7, ash, 7/1…"
              className="flex-1 bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-2.5 text-sm text-[var(--text)] placeholder-[var(--muted)] focus:outline-none focus:border-[var(--teal)]/50 transition-colors"
            />
            <button
              onClick={handleShadeSearch}
              disabled={shadesLoading}
              className="px-3 py-2.5 bg-[var(--surface-2)] border border-[var(--border)] rounded-lg hover:border-[var(--teal)]/40 transition-colors"
            >
              <Search size={14} className="text-[var(--muted)]" />
            </button>
          </div>

          {shades.length > 0 && (
            <div className="mt-2 max-h-40 overflow-y-auto bg-[var(--surface)] border border-[var(--border)] rounded-lg divide-y divide-[var(--border)]">
              {shades.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedShade(s)}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-[var(--surface-2)] transition-colors flex items-center gap-3 ${
                    selectedShade?.id === s.id ? "bg-[var(--teal-dim)]" : ""
                  }`}
                >
                  <span className="mono text-[var(--teal)] w-12 shrink-0">{s.code}</span>
                  <span className="text-[var(--text)] flex-1 truncate">{s.name || "—"}</span>
                  {s.level && (
                    <span className="text-[var(--muted)] shrink-0">Lv {s.level}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {selectedShade && (
            <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-[var(--teal-dim)] border border-[var(--teal)]/20 rounded-lg">
              <span className="text-xs mono text-[var(--teal)]">{selectedShade.code}</span>
              {selectedShade.name && (
                <span className="text-xs text-[var(--text)]">— {selectedShade.name}</span>
              )}
              <button
                onClick={() => setSelectedShade(null)}
                className="ml-auto text-xs text-[var(--muted)] hover:text-[var(--text)]"
              >
                ✕
              </button>
            </div>
          )}
        </div>
      )}

      {/* Client description */}
      <div>
        <label className="block text-xs mono text-[var(--muted)] uppercase tracking-widest mb-2">
          Client & Goal
        </label>
        <textarea
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          placeholder={
            selectedLine
              ? `Describe the client and desired result using ${selectedLine.name}…\n\nExamples:\n• Level 6 natural, 30% gray, medium texture, wants a cool ash brown\n• Dark brunette wanting balayage highlights, fine hair, first lightening service\n• 7NB to a warm golden blonde, currently colored`
              : "Select a color line first, then describe the client and goal…"
          }
          disabled={!selectedLine}
          rows={7}
          className="w-full bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm text-[var(--text)] placeholder-[var(--muted)]/60 focus:outline-none focus:border-[var(--teal)]/50 transition-colors resize-none disabled:opacity-40 leading-relaxed"
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!selectedLine || !userInput.trim()}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-semibold text-sm transition-all
          bg-[var(--teal)] text-black hover:brightness-110 active:scale-[0.99]
          disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:brightness-100"
      >
        <Wand2 size={15} />
        Compute Formula
      </button>
    </div>
  );
}
