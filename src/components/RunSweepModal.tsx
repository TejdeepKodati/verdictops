import React, { useEffect, useState } from "react";
import { Play, X } from "lucide-react";
import type { ByokConfig, EvalRun, ExecuteRunRequest, PipelinePreset } from "../types";

interface RunSweepModalProps {
  open: boolean;
  suiteId: string;
  suiteName: string;
  runs: EvalRun[];
  defaultBaselineId: string;
  byok: ByokConfig;
  onClose: () => void;
  onExecute: (payload: ExecuteRunRequest) => Promise<void>;
}

const PRESETS: { id: PipelinePreset; label: string; description: string }[] = [
  {
    id: "hybrid_rrf",
    label: "Hybrid RRF + Guardrails",
    description: "BM25 + dense semantic concept fusion (RRF) with strict citation & schema guardrails.",
  },
  {
    id: "prompt_guardrailed",
    label: "Prompt Guardrailed v2.4",
    description: "Strict evidence-only synthesis with high dense ranking weight and Pydantic enforcement.",
  },
  {
    id: "bm25_only",
    label: "BM25 Lexical Only",
    description: "Pure keyword Okapi BM25 retriever without semantic bridging; vulnerable to lexical traps.",
  },
  {
    id: "prompt_unconstrained",
    label: "Unconstrained Prompt v3 (Regression Probe)",
    description: "Simulates loosened grounding & markdown prose wrappers to verify CI regression gate catching.",
  },
  {
    id: "custom_weights",
    label: "Custom Retrieval & Guardrail Weights",
    description: "Tune BM25 vs dense RRF weights, guardrail strictness, and schema enforcement directly.",
  },
];

export const RunSweepModal: React.FC<RunSweepModalProps> = ({
  open,
  suiteId,
  suiteName,
  runs,
  defaultBaselineId,
  byok,
  onClose,
  onExecute,
}) => {
  const [pipeline, setPipeline] = useState<PipelinePreset>("hybrid_rrf");
  const [runName, setRunName] = useState("");
  const [baselineId, setBaselineId] = useState(defaultBaselineId);
  const [bm25Weight, setBm25Weight] = useState(0.35);
  const [denseWeight, setDenseWeight] = useState(0.65);
  const [guardrailStrictness, setGuardrailStrictness] = useState(0.92);
  const [schemaEnforcement, setSchemaEnforcement] = useState(true);
  const [useLlmJudge, setUseLlmJudge] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setBaselineId(defaultBaselineId);
  }, [defaultBaselineId, suiteId]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onExecute({
        suite_id: suiteId,
        name: runName.trim() || undefined,
        pipeline,
        baseline_id: baselineId || undefined,
        bm25_weight: bm25Weight,
        dense_weight: denseWeight,
        guardrail_strictness: guardrailStrictness,
        schema_enforcement: schemaEnforcement,
        top_k: 5,
        use_llm_judge: useLlmJudge && Boolean(byok.apiKey.trim()),
      });
      setRunName("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute sweep");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="run-sweep-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto border border-rule bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-rule bg-inset/70 px-5 py-3.5">
          <div>
            <h2 id="run-sweep-title" className="font-serif text-base font-bold text-ink">
              Run Live Evaluation Sweep
            </h2>
            <p className="font-mono text-[11px] text-muted">{suiteName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close run sweep modal"
            className="inline-flex h-8 w-8 items-center justify-center border border-rule bg-surface text-ink hover:bg-inset"
          >
            <X className="h-4 w-4" strokeWidth={1.75} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5 text-xs">
          {error && (
            <div role="alert" className="border border-crimson/40 bg-[#FEF2F2] p-3 text-crimson">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="sweep-name" className="mb-1 block font-semibold text-ink">
              Experiment Run Label (optional)
            </label>
            <input
              id="sweep-name"
              type="text"
              value={runName}
              onChange={(e) => setRunName(e.target.value)}
              placeholder="e.g., Candidate (RRF 0.70 + Rerank)"
              className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
            />
          </div>

          <div>
            <label htmlFor="sweep-baseline" className="mb-1 block font-semibold text-ink">
              Compare Against Baseline
            </label>
            <select
              id="sweep-baseline"
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
              className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <fieldset className="space-y-2">
            <legend className="mb-1 font-semibold text-ink">Pipeline Configuration</legend>
            {PRESETS.map((preset) => {
              const selected = pipeline === preset.id;
              return (
                <label
                  key={preset.id}
                  className={`flex cursor-pointer items-start gap-2.5 border p-2.5 transition-colors ${
                    selected
                      ? "border-burgundy bg-[#FDF2F4]/40"
                      : "border-rule bg-surface hover:bg-inset/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="pipeline-preset"
                    value={preset.id}
                    checked={selected}
                    onChange={() => setPipeline(preset.id)}
                    className="mt-0.5 accent-[#9F1239]"
                  />
                  <div>
                    <div className="font-semibold text-ink">{preset.label}</div>
                    <div className="mt-0.5 text-[11px] text-muted">{preset.description}</div>
                  </div>
                </label>
              );
            })}
          </fieldset>

          {pipeline === "custom_weights" && (
            <div className="space-y-3 border border-rule bg-inset/60 p-3.5">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="space-y-1">
                  <div className="flex justify-between font-medium text-ink">
                    <span>BM25 RRF Weight</span>
                    <span className="font-mono">{bm25Weight.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={bm25Weight}
                    onChange={(e) => setBm25Weight(parseFloat(e.target.value))}
                    className="w-full accent-[#9F1239]"
                  />
                </label>
                <label className="space-y-1">
                  <div className="flex justify-between font-medium text-ink">
                    <span>Dense RRF Weight</span>
                    <span className="font-mono">{denseWeight.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={denseWeight}
                    onChange={(e) => setDenseWeight(parseFloat(e.target.value))}
                    className="w-full accent-[#9F1239]"
                  />
                </label>
              </div>

              <label className="block space-y-1">
                <div className="flex justify-between font-medium text-ink">
                  <span>Grounding Guardrail Strictness</span>
                  <span className="font-mono">{guardrailStrictness.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.2"
                  max="1"
                  step="0.05"
                  value={guardrailStrictness}
                  onChange={(e) => setGuardrailStrictness(parseFloat(e.target.value))}
                  className="w-full accent-[#9F1239]"
                />
              </label>

              <label className="flex items-center gap-2 font-medium text-ink">
                <input
                  type="checkbox"
                  checked={schemaEnforcement}
                  onChange={(e) => setSchemaEnforcement(e.target.checked)}
                  className="accent-[#9F1239]"
                />
                <span>Enforce strict raw JSON Pydantic schema output</span>
              </label>
            </div>
          )}

          <label className="flex items-center gap-2 border border-rule bg-inset/40 px-3 py-2 text-ink">
            <input
              type="checkbox"
              checked={useLlmJudge}
              disabled={!byok.apiKey.trim()}
              onChange={(e) => setUseLlmJudge(e.target.checked)}
              className="accent-[#9F1239]"
            />
            <span className="text-[11px]">
              Run BYOK LLM-as-a-Judge alongside deterministic claim scorer{" "}
              <span className="font-mono text-muted">
                ({byok.apiKey.trim() ? "Key configured" : "Set key in sidebar"})
              </span>
            </span>
          </label>

          <div className="flex justify-end gap-2 border-t border-rule pt-4">
            <button
              type="button"
              onClick={onClose}
              className="border border-rule bg-surface px-4 py-2 font-semibold text-muted hover:text-ink"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-1.5 bg-burgundy px-4 py-2 font-semibold text-white hover:bg-[#881337] disabled:opacity-60"
            >
              <Play className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              <span>{submitting ? "Evaluating Suite..." : "Execute Sweep"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
