import { Sparkles, FlaskConical, AlertTriangle } from "lucide-react";
import type { FormulaResult } from "../api";

interface Props {
  result: FormulaResult | null;
  loading: boolean;
  error: string | null;
  mode: "formula" | "translate";
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ok: "text-emerald-400 border-emerald-900/50 bg-emerald-950/30",
    caution: "text-[var(--amber)] border-[var(--amber)]/30 bg-[var(--amber-dim)]",
    blocked: "text-red-400 border-red-900/50 bg-red-950/30",
    error: "text-red-400 border-red-900/50 bg-red-950/30",
  };
  const cls = colors[status] ?? colors.caution;
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] mono uppercase tracking-widest border ${cls}`}>
      {status}
    </span>
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
      </div>
    );
  }

  const { formula: data } = result;
  const { shade, formula: block, hair_conditions, warnings, assumptions, matched_rules } = data;

  return (
    <div className="h-full overflow-y-auto space-y-4 pr-1">
      <div className="flex items-center gap-2">
        <StatusBadge status={data.status} />
        {result.parse_source && (
          <span className="text-[10px] mono text-[var(--muted)]">parse: {result.parse_source}</span>
        )}
      </div>

      {data.status === "blocked" && warnings.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={14} className="text-red-400" />
            <span className="text-xs font-semibold text-red-400 mono uppercase tracking-widest">
              Blocked
            </span>
          </div>
          <ul className="text-sm text-red-300 space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-[var(--surface)] border border-[var(--teal)]/20 rounded-lg p-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--teal)]/5 to-transparent pointer-events-none" />
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={14} className="text-[var(--teal)]" />
          <span className="text-xs font-semibold mono uppercase tracking-widest text-[var(--teal)]">
            Recommendation
          </span>
        </div>
        <p className="text-sm leading-relaxed text-[var(--text)]">{result.ai_explanation}</p>
        {result.translation_notes && (
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs text-[var(--muted)] italic">
            {result.translation_notes}
          </div>
        )}
      </div>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
        <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-3">
          Selected Shade
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex gap-2">
            <span className="mono text-[var(--teal)] text-lg font-semibold">{shade.shade_code}</span>
            {shade.shade_name && <span className="text-[var(--text)]">{shade.shade_name}</span>}
          </div>
          <div className="text-xs text-[var(--muted)]">
            {shade.brand} · {shade.product_line}
            {shade.level != null && ` · Level ${shade.level}`}
          </div>
          {shade.normalized_tones.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {shade.normalized_tones.map((t) => (
                <span
                  key={t}
                  className="px-2 py-0.5 rounded-full text-[10px] mono bg-[var(--surface-2)] border border-[var(--border)] text-[var(--muted)]"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
        <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-3">
          Formula
        </div>
        <div className="grid gap-3 sm:grid-cols-3 text-sm">
          <div>
            <div className="text-[var(--muted)] text-xs mb-1">Developer</div>
            <div className="mono text-[var(--teal)] font-semibold">{block.developer}</div>
            {block.developer_rationale && (
              <div className="text-xs text-[var(--muted)] mt-1">{block.developer_rationale}</div>
            )}
          </div>
          <div>
            <div className="text-[var(--muted)] text-xs mb-1">Mix Ratio</div>
            <div className="mono text-[var(--text)]">{block.mixing_ratio}</div>
          </div>
          <div>
            <div className="text-[var(--muted)] text-xs mb-1">Processing</div>
            <div className="mono text-[var(--text)]">{block.processing_time}</div>
          </div>
        </div>
        {block.gray_coverage_guidance && (
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs text-[var(--muted)]">
            Gray coverage: {block.gray_coverage_guidance}
          </div>
        )}
      </div>

      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4">
        <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-3">
          Client Profile
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-xs">
          {hair_conditions.natural_level != null && (
            <div><span className="text-[var(--muted)]">Natural level:</span> {hair_conditions.natural_level}</div>
          )}
          {hair_conditions.desired_level != null && (
            <div><span className="text-[var(--muted)]">Desired level:</span> {hair_conditions.desired_level}</div>
          )}
          <div><span className="text-[var(--muted)]">Gray:</span> {hair_conditions.gray_percent}%</div>
          <div><span className="text-[var(--muted)]">Porosity:</span> {hair_conditions.porosity}/10</div>
          <div><span className="text-[var(--muted)]">Elasticity:</span> {hair_conditions.elasticity}/10</div>
          <div><span className="text-[var(--muted)]">Texture:</span> {hair_conditions.texture}</div>
        </div>
      </div>

      {warnings.length > 0 && data.status !== "blocked" && (
        <div className="bg-[var(--amber-dim)] border border-[var(--amber)]/20 rounded-lg p-4">
          <div className="text-xs font-semibold text-[var(--amber)] mono uppercase tracking-widest mb-2">
            Warnings
          </div>
          <ul className="text-sm text-[var(--text)] space-y-1">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {matched_rules.length > 0 && (
        <div className="text-xs text-[var(--muted)]">
          <span className="mono">Matched rules:</span> {matched_rules.join(", ")}
        </div>
      )}

      {assumptions.length > 0 && (
        <div className="text-xs text-[var(--muted)] italic">
          {assumptions.join(" ")}
        </div>
      )}

      <details className="group">
        <summary className="cursor-pointer text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors mono select-none py-2">
          ▶ structured input
        </summary>
        <pre className="mt-2 text-xs mono text-[var(--muted)] bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(result.structured_request, null, 2)}
        </pre>
      </details>

      <details className="group">
        <summary className="cursor-pointer text-xs text-[var(--muted)] hover:text-[var(--text)] transition-colors mono select-none py-2">
          ▶ raw engine output
        </summary>
        <pre className="mt-2 text-xs mono text-[var(--muted)] bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}
