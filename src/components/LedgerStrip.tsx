import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Save,
  ShieldAlert,
  SlidersHorizontal,
} from "lucide-react";
import type { CompareResponse, GatePolicy } from "../types";

interface LedgerStripProps {
  comparison: CompareResponse;
  onSavePolicy: (policy: Omit<GatePolicy, "suite_id">) => Promise<void>;
}

function formatDelta(val: number, decimals: number = 3, suffix: string = ""): string {
  const sign = val > 0 ? "+" : val < 0 ? "-" : "+";
  return `${sign}${Math.abs(val).toFixed(decimals)}${suffix}`;
}

export const LedgerStrip: React.FC<LedgerStripProps> = ({ comparison, onSavePolicy }) => {
  const [policyOpen, setPolicyOpen] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [draftPolicy, setDraftPolicy] = useState<Omit<GatePolicy, "suite_id">>({
    min_ndcg: comparison.applied_policy.min_ndcg,
    min_faithfulness: comparison.applied_policy.min_faithfulness,
    min_schema_pass: comparison.applied_policy.min_schema_pass,
    min_tool_f1: comparison.applied_policy.min_tool_f1,
    max_ndcg_drop: comparison.applied_policy.max_ndcg_drop,
    max_faithfulness_drop: comparison.applied_policy.max_faithfulness_drop,
    max_p95_latency_ms: comparison.applied_policy.max_p95_latency_ms,
  });

  useEffect(() => {
    setDraftPolicy({
      min_ndcg: comparison.applied_policy.min_ndcg,
      min_faithfulness: comparison.applied_policy.min_faithfulness,
      min_schema_pass: comparison.applied_policy.min_schema_pass,
      min_tool_f1: comparison.applied_policy.min_tool_f1,
      max_ndcg_drop: comparison.applied_policy.max_ndcg_drop,
      max_faithfulness_drop: comparison.applied_policy.max_faithfulness_drop,
      max_p95_latency_ms: comparison.applied_policy.max_p95_latency_ms,
    });
  }, [comparison.suite.id, comparison.applied_policy]);

  const { suite, baseline_run, candidate_run, deltas, gate_verdict, violated_rules, applied_policy } =
    comparison;
  const cm = candidate_run.metrics;
  const isPass = gate_verdict === "PASS";

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(comparison, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `verdictops-${suite.id}-${candidate_run.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePolicySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPolicy(true);
    try {
      await onSavePolicy(draftPolicy);
      setPolicyOpen(false);
    } finally {
      setSavingPolicy(false);
    }
  };

  const deltaTone = (val: number, invertBetter: boolean = false): string => {
    if (Math.abs(val) < 0.0005) return "text-muted";
    const good = invertBetter ? val < 0 : val > 0;
    return good ? "text-forest" : "text-burgundy";
  };

  return (
    <header className="space-y-4">
      {/* Suite Masthead */}
      <div className="flex flex-col gap-3 border-b border-rule pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="font-mono text-[11px] uppercase tracking-wider text-burgundy">
            {suite.subtitle}
          </div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-ink sm:text-3xl">
            {suite.name}
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-muted">{suite.description}</p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setPolicyOpen((v) => !v)}
            aria-expanded={policyOpen}
            className="inline-flex items-center gap-1.5 border border-rule bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition-colors hover:bg-inset"
          >
            <SlidersHorizontal className="h-3.5 w-3.5 text-muted" strokeWidth={1.75} aria-hidden="true" />
            <span>Gate Policy</span>
          </button>

          <button
            type="button"
            onClick={handleExportJson}
            className="inline-flex items-center gap-1.5 border border-rule bg-surface px-3 py-1.5 text-xs font-semibold text-ink transition-colors hover:bg-inset"
          >
            <Download className="h-3.5 w-3.5 text-muted" strokeWidth={1.75} aria-hidden="true" />
            <span>Export Diff</span>
          </button>
        </div>
      </div>

      {/* Collapsible Gate Threshold Configurator */}
      {policyOpen && (
        <form
          onSubmit={handlePolicySubmit}
          className="border border-rule bg-inset/70 p-4 text-xs"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <h2 className="font-serif text-sm font-bold text-ink">
              CI Regression Gate Thresholds ({suite.id})
            </h2>
            <span className="font-mono text-[11px] text-muted">Persisted in SQLite</span>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <label className="space-y-1">
              <span className="block font-medium text-muted">Min NDCG@5</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={draftPolicy.min_ndcg}
                onChange={(e) =>
                  setDraftPolicy({ ...draftPolicy, min_ndcg: parseFloat(e.target.value) || 0 })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
            <label className="space-y-1">
              <span className="block font-medium text-muted">Min Faithfulness</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={draftPolicy.min_faithfulness}
                onChange={(e) =>
                  setDraftPolicy({
                    ...draftPolicy,
                    min_faithfulness: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
            <label className="space-y-1">
              <span className="block font-medium text-muted">Min Schema Ratio</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={draftPolicy.min_schema_pass}
                onChange={(e) =>
                  setDraftPolicy({
                    ...draftPolicy,
                    min_schema_pass: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
            <label className="space-y-1">
              <span className="block font-medium text-muted">Min Tool F1</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={draftPolicy.min_tool_f1}
                onChange={(e) =>
                  setDraftPolicy({ ...draftPolicy, min_tool_f1: parseFloat(e.target.value) || 0 })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
            <label className="space-y-1">
              <span className="block font-medium text-muted">Max NDCG Drop</span>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={draftPolicy.max_ndcg_drop}
                onChange={(e) =>
                  setDraftPolicy({
                    ...draftPolicy,
                    max_ndcg_drop: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
            <label className="space-y-1">
              <span className="block font-medium text-muted">Max p95 (ms)</span>
              <input
                type="number"
                step="10"
                min="50"
                value={draftPolicy.max_p95_latency_ms}
                onChange={(e) =>
                  setDraftPolicy({
                    ...draftPolicy,
                    max_p95_latency_ms: parseFloat(e.target.value) || 100,
                  })
                }
                className="w-full border border-rule bg-surface px-2 py-1.5 font-mono text-xs text-ink"
              />
            </label>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setPolicyOpen(false)}
              className="border border-rule bg-surface px-3 py-1.5 text-xs font-medium text-muted hover:text-ink"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={savingPolicy}
              className="inline-flex items-center gap-1.5 bg-burgundy px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#881337] disabled:opacity-60"
            >
              <Save className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              <span>{savingPolicy ? "Saving..." : "Apply Policy"}</span>
            </button>
          </div>
        </form>
      )}

      {/* Comparison Context Line */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>
            <strong className="font-semibold text-ink">Baseline:</strong> {baseline_run.name}
          </span>
          <span aria-hidden="true" className="text-rule">
            |
          </span>
          <span>
            <strong className="font-semibold text-ink">Candidate:</strong> {candidate_run.name}
          </span>
        </div>
        <span className="font-mono text-[11px]">
          {candidate_run.prompt_version} · {candidate_run.model_name}
        </span>
      </div>

      {/* Horizontal Ledger Summary Strip (hairline dividers + strong bottom rule) */}
      <section
        aria-label="Evaluation Ledger Summary Strip"
        className="ledger-double-rule border-t border-rule bg-surface"
      >
        <div className="grid grid-cols-2 divide-y divide-rule sm:grid-cols-3 lg:grid-cols-6 lg:divide-x lg:divide-y-0">
          {/* 1. CI Gate Verdict */}
          <div className="flex flex-col justify-between border-r border-rule p-3.5 lg:border-r-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              CI Gate Verdict
            </div>
            <div className="mt-1.5 flex items-center gap-2">
              {isPass ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-forest" strokeWidth={2} aria-hidden="true" />
              ) : (
                <ShieldAlert className="h-5 w-5 shrink-0 text-crimson" strokeWidth={2} aria-hidden="true" />
              )}
              <span
                className={`font-serif text-xl font-bold tracking-tight ${
                  isPass ? "text-forest" : "text-crimson"
                }`}
              >
                {gate_verdict}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              {cm.passed_cases}/{cm.total_cases} cases passed
            </div>
          </div>

          {/* 2. NDCG@5 */}
          <div className="flex flex-col justify-between p-3.5 sm:border-r sm:border-rule lg:border-r-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              NDCG@5
            </div>
            <div className="mt-1.5 flex items-baseline gap-2">
              <span className="font-mono text-xl font-semibold text-ink">
                {cm.ndcg_at_5.toFixed(3)}
              </span>
              <span className={`font-mono text-xs font-medium ${deltaTone(deltas.ndcg_at_5)}`}>
                {formatDelta(deltas.ndcg_at_5, 3)}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              MRR {cm.mrr.toFixed(3)} · R@5 {cm.recall_at_5.toFixed(2)}
            </div>
          </div>

          {/* 3. Faithfulness */}
          <div className="flex flex-col justify-between border-r border-rule p-3.5 sm:border-r-0 lg:border-r-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              Faithfulness
            </div>
            <div className="mt-1.5 flex items-baseline gap-2">
              <span className="font-mono text-xl font-semibold text-ink">
                {cm.faithfulness.toFixed(3)}
              </span>
              <span className={`font-mono text-xs font-medium ${deltaTone(deltas.faithfulness)}`}>
                {formatDelta(deltas.faithfulness, 3)}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              Gate &gt;= {applied_policy.min_faithfulness.toFixed(2)}
            </div>
          </div>

          {/* 4. Schema Pass % */}
          <div className="flex flex-col justify-between p-3.5 sm:border-r sm:border-rule lg:border-r-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              Schema Pass %
            </div>
            <div className="mt-1.5 flex items-baseline gap-2">
              <span className="font-mono text-xl font-semibold text-ink">
                {(cm.schema_pass_rate * 100).toFixed(1)}%
              </span>
              <span
                className={`font-mono text-xs font-medium ${deltaTone(deltas.schema_pass_rate)}`}
              >
                {formatDelta(deltas.schema_pass_rate * 100, 1, "%")}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              Gate &gt;= {(applied_policy.min_schema_pass * 100).toFixed(0)}%
            </div>
          </div>

          {/* 5. Tool Sequence F1 */}
          <div className="flex flex-col justify-between border-r border-rule p-3.5 lg:border-r-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              Tool Seq F1
            </div>
            <div className="mt-1.5 flex items-baseline gap-2">
              <span className="font-mono text-xl font-semibold text-ink">
                {cm.tool_f1.toFixed(3)}
              </span>
              <span className={`font-mono text-xs font-medium ${deltaTone(deltas.tool_f1)}`}>
                {formatDelta(deltas.tool_f1, 3)}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              Gate &gt;= {applied_policy.min_tool_f1.toFixed(2)}
            </div>
          </div>

          {/* 6. p95 Latency */}
          <div className="flex flex-col justify-between p-3.5">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              p95 Latency
            </div>
            <div className="mt-1.5 flex items-baseline gap-2">
              <span className="font-mono text-xl font-semibold text-ink">
                {cm.p95_latency_ms.toFixed(0)}ms
              </span>
              <span
                className={`font-mono text-xs font-medium ${
                  deltas.p95_latency_ms > 80
                    ? "text-ochre-text"
                    : deltaTone(deltas.p95_latency_ms, true)
                }`}
              >
                {formatDelta(deltas.p95_latency_ms, 0, "ms")}
              </span>
            </div>
            <div className="mt-1 font-mono text-[11px] text-muted">
              Budget &lt;= {applied_policy.max_p95_latency_ms.toFixed(0)}ms
            </div>
          </div>
        </div>
      </section>

      {/* Violated Gate Rules Alert Banner */}
      {!isPass && violated_rules.length > 0 && (
        <div
          role="alert"
          className="border border-crimson/30 border-l-4 border-l-crimson bg-[#FEF2F2] px-4 py-3"
        >
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-crimson">
            <AlertTriangle className="h-4 w-4 shrink-0" strokeWidth={2} aria-hidden="true" />
            <span>CI Regression Gate Blocked ({violated_rules.length} rule violation{violated_rules.length > 1 ? "s" : ""})</span>
          </div>
          <ul className="mt-2 space-y-1 text-xs text-ink">
            {violated_rules.map((vr) => (
              <li key={vr.rule} className="flex flex-wrap items-baseline gap-x-2">
                <code className="font-mono font-semibold text-crimson">{vr.rule}</code>
                <span>{vr.message}</span>
                <span className="font-mono text-[11px] text-muted">
                  (expected {vr.expected}, actual {vr.actual})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
};
