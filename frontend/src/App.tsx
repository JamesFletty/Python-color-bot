import { useState, useEffect } from "react";
import { FlaskConical, ArrowRightLeft, Zap, Database, AlertCircle } from "lucide-react";
import type { Brand, AIFormulaResponse } from "./api";
import { fetchBrands } from "./api";
import FormulaMode from "./components/FormulaMode";
import TranslateMode from "./components/TranslateMode";
import ResultPanel from "./components/ResultPanel";

type Mode = "formula" | "translate";

export default function App() {
  const [mode, setMode] = useState<Mode>("formula");
  const [brands, setBrands] = useState<Brand[]>([]);
  const [brandsError, setBrandsError] = useState<string | null>(null);
  const [result, setResult] = useState<AIFormulaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBrands()
      .then(setBrands)
      .catch((e: unknown) =>
        setBrandsError(e instanceof Error ? e.message : "Failed to load brands")
      );
  }, []);

  function handleModeChange(m: Mode) {
    setMode(m);
    setResult(null);
    setError(null);
  }

  const totalLines = brands.reduce((sum, b) => sum + b.lines.length, 0);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)]">
      {/* Header */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)]/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-[var(--teal)]/10 border border-[var(--teal)]/30 flex items-center justify-center">
              <FlaskConical size={14} className="text-[var(--teal)]" />
            </div>
            <span className="font-bold text-base tracking-tight text-[var(--text)]">
              Color<span className="text-[var(--teal)] glow-teal">Synth</span>
            </span>
            <span className="hidden sm:flex items-center gap-1 px-2 py-0.5 bg-[var(--teal)]/10 border border-[var(--teal)]/20 rounded-full">
              <Zap size={9} className="text-[var(--teal)]" />
              <span className="text-[10px] mono text-[var(--teal)] font-medium">AI-POWERED</span>
            </span>
          </div>

          {/* Status */}
          <div className="flex items-center gap-4">
            {brands.length > 0 && (
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-[var(--muted)]">
                <Database size={11} />
                <span className="mono">{brands.length} brands</span>
                <span className="opacity-40">·</span>
                <span className="mono">{totalLines} lines</span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-[var(--muted)] mono hidden sm:inline">ONLINE</span>
            </div>
          </div>
        </div>
      </header>

      {/* Mode toggle */}
      <div className="border-b border-[var(--border)] bg-[var(--surface)]/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex">
            <button
              onClick={() => handleModeChange("formula")}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-all ${
                mode === "formula"
                  ? "border-[var(--teal)] text-[var(--teal)]"
                  : "border-transparent text-[var(--muted)] hover:text-[var(--text)]"
              }`}
            >
              <FlaskConical size={14} />
              Get Formula
            </button>
            <button
              onClick={() => handleModeChange("translate")}
              className={`flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-all ${
                mode === "translate"
                  ? "border-[var(--amber)] text-[var(--amber)]"
                  : "border-transparent text-[var(--muted)] hover:text-[var(--text)]"
              }`}
            >
              <ArrowRightLeft size={14} />
              Translate Formula
            </button>
          </div>
        </div>
      </div>

      {/* Brand load error */}
      {brandsError && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 mt-4">
          <div className="flex items-center gap-2 px-4 py-3 bg-red-950/40 border border-red-900/40 rounded-lg text-xs text-red-400">
            <AlertCircle size={13} />
            Failed to load color catalog: {brandsError}
          </div>
        </div>
      )}

      {/* Main layout */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6 h-full">
          {/* Left panel — inputs */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 self-start">
            <div className="flex items-center gap-2 mb-5 pb-4 border-b border-[var(--border)]">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  mode === "formula" ? "bg-[var(--teal)]" : "bg-[var(--amber)]"
                }`}
              />
              <span className="text-xs mono text-[var(--muted)] uppercase tracking-widest">
                {mode === "formula" ? "Formula Builder" : "Formula Translator"}
              </span>
            </div>

            {mode === "formula" ? (
              <FormulaMode
                brands={brands}
                onResult={(r) => { setResult(r); setError(null); }}
                onLoading={setLoading}
                onError={setError}
              />
            ) : (
              <TranslateMode
                brands={brands}
                onResult={(r) => { setResult(r); setError(null); }}
                onLoading={setLoading}
                onError={setError}
              />
            )}
          </div>

          {/* Right panel — results */}
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-5 min-h-[520px] lg:min-h-0">
            <div className="flex items-center gap-2 mb-5 pb-4 border-b border-[var(--border)]">
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  result
                    ? mode === "formula"
                      ? "bg-[var(--teal)] animate-pulse"
                      : "bg-[var(--amber)] animate-pulse"
                    : "bg-[var(--muted)]"
                }`}
              />
              <span className="text-xs mono text-[var(--muted)] uppercase tracking-widest">
                {result ? "Formula Output" : "Awaiting Input"}
              </span>
              {result && !loading && (
                <button
                  onClick={() => { setResult(null); setError(null); }}
                  className="ml-auto text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors mono"
                >
                  clear
                </button>
              )}
            </div>

            <div className="h-[calc(100%-3rem)]">
              <ResultPanel
                result={result}
                loading={loading}
                error={error}
                mode={mode}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-3 px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-xs text-[var(--muted)]">
          <span className="mono opacity-50">COLORSYNTH v2</span>
          <span className="opacity-40">Professional use only · Always verify formulas before application</span>
        </div>
      </footer>
    </div>
  );
}
