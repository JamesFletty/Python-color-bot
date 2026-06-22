import { Sparkles, FlaskConical, ChevronRight, AlertTriangle } from "lucide-react";
import type { AIFormulaResponse } from "../api";

interface Props {
  result: AIFormulaResponse | null;
  loading: boolean;
  error: string | null;
  mode: "formula" | "translate";
}

function FormulaValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-[var(--muted)]">—</span>;
  if (typeof value === "object" && !Array.isArray(value)) {
    return (
      <div className="pl-3 border-l border-[var(--border)] space-y-1 mt-1 min-w-0">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="flex gap-2 text-xs min-w-0">
            <span className="text-[var(--muted)] shrink-0">{k}:</span>
            <div className="min-w-0 flex-1">
              <FormulaValue value={v} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-[var(--muted)]">[]</span>;
    return (
      <div className="space-y-1 min-w-0">
        {value.map((item, i) => (
          <div key={i} className="flex items-start gap-1 min-w-0">
            <ChevronRight size={10} className="mt-0.5 text-[var(--teal)] shrink-0" />
            <div className="min-w-0 flex-1">
              <FormulaValue value={item} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  return (
    <span className="mono text-[var(--teal)] text-xs break-words [overflow-wrap:anywhere]">
      {String(value)}
    </span>
  );
}

function FormulaSection({
  title,
  data,
}: {
  title: string;
  data: Record<string, unknown>;
}) {
  const entries = Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0));
  if (entries.length === 0) return null;
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
      <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-3">
        {title}
      </div>
      <div className="space-y-2">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className="flex flex-col gap-0.5 sm:grid sm:grid-cols-[150px_1fr] sm:gap-2 sm:items-start text-xs min-w-0"
          >
            <span className="text-[var(--muted)] sm:truncate sm:pt-0.5">{key.replace(/_/g, " ")}</span>
            <div className="min-w-0">
              <FormulaValue value={value} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ResultPanel({ result, loading, error, mode }: Props) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-[var(--muted)]">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-2 border-[var(--border)] animate-spin border-t-[var(--teal)]" />
          <FlaskConical size={20} className="absolute inset-0 m-auto text-[var(--teal)]" />
        </div>
        <div className="text-sm mono animate-pulse">
          {mode === "translate" ? "Translating formula..." : "Computing formula..."}
        </div>
        <div className="text-xs text-[var(--muted)] opacity-60">AI is analyzing your input</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 px-8 text-center">
        <AlertTriangle size={32} className="text-red-400 opacity-70" />
        <div className="text-sm text-red-400">Formula Error</div>
        <div className="text-xs text-[var(--muted)] bg-[var(--surface)] border border-red-900/40 rounded-lg px-4 py-3 font-mono leading-relaxed max-w-md">
          {error}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-[var(--muted)]">
        <FlaskConical size={48} className="opacity-20" />
        <div className="text-sm">
          {mode === "translate" ? "Enter a formula to translate" : "Describe your client to get started"}
        </div>
        <div className="text-xs opacity-60 text-center max-w-xs">
          {mode === "translate"
            ? "Paste any formula — the AI will map it to your target line"
            : "Use natural language or shade codes — the AI handles the rest"}
        </div>
      </div>
    );
  }

  const formula = result.formula as Record<string, unknown>;
  const engineFailed = result.status === "error" || formula.status === "error";
  const engineError =
    typeof formula.error === "string"
      ? formula.error
      : engineFailed
        ? "The formula engine could not complete this request."
        : null;
  const structured = result.structured_request as Record<string, unknown> | undefined;
  const groundingNote =
    typeof structured?.grounding_note === "string" ? structured.grounding_note : null;

  const topKeys = ["shade", "shade_code", "shade_name", "color_line", "line", "product_line", "brand"];
  const devKeys = ["developer", "developer_strength", "developer_volume", "developer_options", "mixing_ratio", "ratio"];
  const processKeys = ["processing_time", "processing_time_minutes", "timing", "application_notes", "notes"];
  const metaKeys = ["service_intent", "gray_coverage", "gray", "current_level", "desired_level", "texture", "porosity", "elasticity"];
  const skipKeys = ["components", "formula_rule", ...topKeys, ...devKeys, ...processKeys, ...metaKeys];

  function pick(keys: string[]): Record<string, unknown> {
    return Object.fromEntries(
      Object.entries(formula).filter(([k]) => keys.some((kk) => k.toLowerCase().includes(kk)))
    );
  }

  function omit(keys: string[]): Record<string, unknown> {
    return Object.fromEntries(
      Object.entries(formula).filter(([k]) => !keys.some((kk) => k.toLowerCase().includes(kk)))
    );
  }

  const components = Array.isArray(formula.components) ? formula.components as Array<{product: string; grams: number; role: string}> : null;
  const formulaRule = typeof formula.formula_rule === "string" ? formula.formula_rule : null;
  const developer = typeof formula.developer === "string" ? formula.developer : null;
  const mixingRatio = typeof formula.mixing_ratio === "string" ? formula.mixing_ratio : null;

  const allPickedKeys = skipKeys;
  const shadeSection = pick(topKeys);
  const devSection = components ? {} : pick(devKeys);
  const processSection = pick(processKeys);
  const metaSection = pick(metaKeys);
  const remainingSection = omit(allPickedKeys);

  return (
    <div className="h-full overflow-y-auto space-y-4 pr-1">
      {engineFailed && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={14} className="text-red-400" />
            <span className="text-xs font-semibold text-red-400 mono uppercase tracking-widest">
              Engine Error
            </span>
          </div>
          <p className="text-sm text-red-300 leading-relaxed">{engineError}</p>
          {structured?.shade != null && (
            <p className="mt-2 text-xs text-[var(--muted)] mono">
              AI translated to shade: {String(structured.shade)}
            </p>
          )}
        </div>
      )}

      {structured && Object.keys(structured).length > 0 && (
        <details className="group bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
          <summary className="cursor-pointer text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors mono select-none">
            ▶ structured engine input (AI → deterministic engine)
          </summary>
          <pre className="mt-3 text-xs mono text-[var(--muted)] overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(structured, null, 2)}
          </pre>
        </details>
      )}

      {/* AI Explanation */}
      <div
        className={`bg-[var(--surface)] border rounded-lg p-4 relative overflow-hidden ${
          engineFailed ? "border-[var(--border)]" : "border-[var(--teal)]/20"
        }`}
      >
        {!engineFailed && (
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--teal)]/5 to-transparent pointer-events-none" />
        )}
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={14} className={engineFailed ? "text-[var(--muted)]" : "text-[var(--teal)]"} />
          <span
            className={`text-xs font-semibold mono uppercase tracking-widest ${
              engineFailed ? "text-[var(--muted)]" : "text-[var(--teal)]"
            }`}
          >
            {engineFailed ? "AI Notes" : "AI Recommendation"}
          </span>
        </div>
        <p className={`text-sm leading-relaxed ${engineFailed ? "text-[var(--muted)]" : "text-[var(--text)]"}`}>
          {result.ai_explanation}
        </p>
        {(result.translation_notes || groundingNote) && (
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs text-[var(--muted)] italic">
            {result.translation_notes || groundingNote}
          </div>
        )}
      </div>

      {/* Multi-component formula (e.g. Aveda Intense Series) */}
      {components && components.length > 0 && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
          <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-3">
            Formula
          </div>
          <div className="space-y-2 mb-3">
            {components.map((c, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="mono text-[var(--teal)] font-semibold w-10 text-right shrink-0">
                  {c.grams}g
                </span>
                <span className="text-[var(--text)]">{c.product}</span>
                <span className="text-[var(--muted)] text-xs ml-auto">{c.role}</span>
              </div>
            ))}
            <div className="flex items-center gap-3 text-sm pt-1 border-t border-[var(--border)] mt-2">
              <span className="mono text-[var(--teal)] font-semibold w-10 text-right shrink-0">dev</span>
              <span className="text-[var(--text)]">
                {developer}{mixingRatio ? ` · ${mixingRatio}` : ""}
              </span>
            </div>
          </div>
          {formulaRule && (
            <div className="text-xs text-[var(--muted)] mt-1 mono opacity-60">{formulaRule}</div>
          )}
        </div>
      )}

      {/* Formula sections */}
      {Object.keys(shadeSection).length > 0 && (
        <FormulaSection title="Selected Shade" data={shadeSection} />
      )}
      {Object.keys(devSection).length > 0 && (
        <FormulaSection title="Developer & Mix" data={devSection} />
      )}
      {Object.keys(processSection).length > 0 && (
        <FormulaSection title="Processing" data={processSection} />
      )}
      {Object.keys(metaSection).length > 0 && (
        <FormulaSection title="Client Profile" data={metaSection} />
      )}
      {Object.keys(remainingSection).length > 0 && (
        <FormulaSection title="Additional Data" data={remainingSection} />
      )}

      {/* Raw output toggle */}
      <details className="group">
        <summary className="cursor-pointer text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors mono select-none py-2">
          ▶ raw engine output
        </summary>
        <pre className="mt-2 text-xs mono text-[var(--muted)] bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(result.formula, null, 2)}
        </pre>
      </details>
    </div>
  );
}
