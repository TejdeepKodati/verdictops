import React from "react";
import {
  AlertOctagon,
  CheckCircle2,
  FileSearch,
  GitBranch,
  ShieldCheck,
  TerminalSquare,
  XCircle,
} from "lucide-react";
import type { CaseDiffItem, ClaimVerdict } from "../types";

interface CaseInspectorProps {
  item: CaseDiffItem;
}

function tryPrettyOutput(raw: string): string {
  const trimmed = raw.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      return JSON.stringify(JSON.parse(trimmed), null, 2);
    } catch {
      return raw;
    }
  }
  return raw;
}

function claimBadgeClasses(verdict: ClaimVerdict): string {
  switch (verdict) {
    case "SUPPORTED":
      return "border-forest/30 bg-[#ECFDF5] text-forest";
    case "PARTIAL":
      return "border-ochre/30 bg-[#FEF3C7] text-ochre-text";
    case "UNSUPPORTED":
      return "border-crimson/30 bg-[#FEF2F2] text-crimson";
  }
}

export const CaseInspector: React.FC<CaseInspectorProps> = ({ item }) => {
  const { case: evalCase, baseline, candidate } = item;
  const relevantEntries = Object.entries(evalCase.relevant_docs);

  return (
    <div className="space-y-5 border-t border-rule bg-inset/75 p-4 text-xs text-ink sm:p-5">
      {/* Query & Failure Diagnostics */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="min-w-0 border border-rule bg-surface p-3.5 lg:col-span-2">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted">
              Golden Query · {evalCase.category}
            </span>
            <span className="font-mono text-[11px] text-muted">{evalCase.case_code}</span>
          </div>
          <p className="text-sm font-medium leading-relaxed text-ink [overflow-wrap:anywhere]">
            {evalCase.query}
          </p>
          {evalCase.expected_claims.length > 0 && (
            <div className="mt-2.5 border-t border-rule pt-2">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
                Expected Claims
              </div>
              <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted">
                {evalCase.expected_claims.map((claim, idx) => (
                  <li key={idx} className="[overflow-wrap:anywhere]">
                    {claim}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="min-w-0 border border-rule bg-surface p-3.5">
          <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-muted">
            {candidate.passed ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-forest" strokeWidth={2} aria-hidden="true" />
            ) : (
              <AlertOctagon className="h-3.5 w-3.5 text-crimson" strokeWidth={2} aria-hidden="true" />
            )}
            <span>Candidate Verdict</span>
          </div>
          {candidate.passed ? (
            <p className="text-xs leading-relaxed text-forest [overflow-wrap:anywhere]">
              Passed all grounding, retrieval, schema, and tool-sequence thresholds.
            </p>
          ) : (
            <ul className="space-y-1 text-xs text-crimson">
              {candidate.failure_reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-1.5">
                  <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" strokeWidth={2} aria-hidden="true" />
                  <span className="min-w-0 [overflow-wrap:anywhere]">{reason}</span>
                </li>
              ))}
            </ul>
          )}
          {candidate.forbidden_hits.length > 0 && (
            <div className="mt-2.5 border-t border-crimson/20 pt-2">
              <div className="font-mono text-[10px] font-bold uppercase text-crimson">
                Triggered Forbidden Claims
              </div>
              <ul className="mt-1 space-y-1 text-[11px] text-crimson">
                {candidate.forbidden_hits.map((hit, idx) => (
                  <li key={idx} className="[overflow-wrap:anywhere]">
                    • {hit}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Side-by-Side Baseline vs Candidate Output */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="min-w-0 border border-rule bg-surface p-3.5">
          <div className="mb-2 flex items-center justify-between gap-2 border-b border-rule pb-2">
            <span className="font-serif text-xs font-bold text-ink">
              Baseline Output
            </span>
            <span className="font-mono text-[11px] text-muted">
              Faith {baseline.faithfulness_score.toFixed(3)} · {baseline.latency_ms.toFixed(0)}ms
            </span>
          </div>
          <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] leading-relaxed text-ink">
            {tryPrettyOutput(baseline.predicted_output)}
          </pre>
        </div>

        <div
          className={`min-w-0 border bg-surface p-3.5 ${
            candidate.passed ? "border-forest/40" : "border-burgundy/60"
          }`}
        >
          <div className="mb-2 flex items-center justify-between gap-2 border-b border-rule pb-2">
            <span className="font-serif text-xs font-bold text-ink">
              Candidate Output
            </span>
            <span className="font-mono text-[11px] text-muted">
              Faith {candidate.faithfulness_score.toFixed(3)} · {candidate.latency_ms.toFixed(0)}ms
            </span>
          </div>
          <pre className="max-h-56 overflow-y-auto whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] leading-relaxed text-ink">
            {tryPrettyOutput(candidate.predicted_output)}
          </pre>
        </div>
      </div>

      {/* Retrieved Doc IDs vs Ground Truth */}
      <div className="border border-rule bg-surface p-3.5">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2">
          <div className="flex items-center gap-1.5 font-serif text-xs font-bold text-ink">
            <FileSearch className="h-3.5 w-3.5 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
            <span>Retrieval Ranking Comparison (Top-K vs Ground Truth)</span>
          </div>
          <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] text-muted">
            <span>
              NDCG@5: {baseline.ndcg_at_5.toFixed(3)} -&gt;{" "}
              <strong className="text-ink">{candidate.ndcg_at_5.toFixed(3)}</strong>
            </span>
            <span>
              MRR: {baseline.mrr.toFixed(3)} -&gt;{" "}
              <strong className="text-ink">{candidate.mrr.toFixed(3)}</strong>
            </span>
            <span>
              Recall@5: {baseline.recall_at_5.toFixed(2)} -&gt;{" "}
              <strong className="text-ink">{candidate.recall_at_5.toFixed(2)}</strong>
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="min-w-0">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
              Ground Truth Relevant
            </div>
            <div className="flex flex-wrap gap-1.5">
              {relevantEntries.length === 0 ? (
                <span className="text-muted">None specified</span>
              ) : (
                relevantEntries.map(([docId, rel]) => (
                  <span
                    key={docId}
                    className="border border-forest/30 bg-[#ECFDF5] px-2 py-0.5 font-mono text-[11px] text-forest"
                  >
                    {docId} (rel={rel})
                  </span>
                ))
              )}
            </div>
          </div>

          <div className="min-w-0">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
              Baseline Ranked IDs
            </div>
            <div className="flex flex-wrap gap-1.5">
              {baseline.retrieved_doc_ids.map((docId, idx) => {
                const rel = evalCase.relevant_docs[docId] ?? 0;
                return (
                  <span
                    key={`${docId}-${idx}`}
                    className={`border px-2 py-0.5 font-mono text-[11px] ${
                      rel > 0
                        ? "border-forest/30 bg-[#ECFDF5] text-forest"
                        : "border-rule bg-inset text-muted"
                    }`}
                  >
                    #{idx + 1} {docId}
                    {rel > 0 ? ` (rel=${rel})` : ""}
                  </span>
                );
              })}
            </div>
          </div>

          <div className="min-w-0">
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
              Candidate Ranked IDs
            </div>
            <div className="flex flex-wrap gap-1.5">
              {candidate.retrieved_doc_ids.map((docId, idx) => {
                const rel = evalCase.relevant_docs[docId] ?? 0;
                return (
                  <span
                    key={`${docId}-${idx}`}
                    className={`border px-2 py-0.5 font-mono text-[11px] ${
                      rel > 0
                        ? "border-forest/30 bg-[#ECFDF5] text-forest"
                        : "border-burgundy/25 bg-[#FDF2F4] text-burgundy"
                    }`}
                  >
                    #{idx + 1} {docId}
                    {rel > 0 ? ` (rel=${rel})` : " (distractor)"}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Atomic Claim Grounding Verdicts */}
      <div className="border border-rule bg-surface p-3.5">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 border-b border-rule pb-2">
          <div className="flex items-center gap-1.5 font-serif text-xs font-bold text-ink">
            <ShieldCheck className="h-3.5 w-3.5 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
            <span>
              Candidate Atomic Claim Faithfulness ({candidate.claim_traces.length} claim
              {candidate.claim_traces.length === 1 ? "" : "s"})
            </span>
          </div>
          <div className="font-mono text-[11px] text-muted">
            Score: <strong className="text-ink">{candidate.faithfulness_score.toFixed(4)}</strong>{" "}
            · Mode: {candidate.judge_mode}
            {candidate.llm_judge_score !== null &&
              ` · LLM Judge: ${candidate.llm_judge_score.toFixed(3)}`}
          </div>
        </div>

        {candidate.llm_judge_rationale && (
          <div className="mb-2.5 border border-rule bg-inset px-3 py-2 text-[11px] text-ink">
            <strong className="font-mono">BYOK Judge Note:</strong> {candidate.llm_judge_rationale}
          </div>
        )}

        {candidate.claim_traces.length === 0 ? (
          <p className="text-muted">No prose atomic claims extracted from structured payload.</p>
        ) : (
          <div className="divide-y divide-rule">
            {candidate.claim_traces.map((trace, idx) => (
              <div key={idx} className="min-w-0 py-2.5 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="min-w-0 flex-1 font-sans text-xs leading-relaxed text-ink [overflow-wrap:anywhere]">
                    {trace.claim}
                  </p>
                  <span
                    className={`shrink-0 border px-2 py-0.5 font-mono text-[10px] font-semibold ${claimBadgeClasses(
                      trace.verdict,
                    )}`}
                  >
                    {trace.verdict}
                  </span>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted">
                  <span className="[overflow-wrap:anywhere]">{trace.reason}</span>
                  {trace.matched_doc_id && <span>Evidence: {trace.matched_doc_id}</span>}
                  <span>Overlap: {trace.token_overlap.toFixed(2)}</span>
                  <span>IDF-Bigram: {trace.idf_bigram_similarity.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Schema Contract & Tool-Call Sequence Assertions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="min-w-0 border border-rule bg-surface p-3.5">
          <div className="mb-2 flex items-center justify-between gap-2 border-b border-rule pb-2">
            <div className="flex items-center gap-1.5 font-serif text-xs font-bold text-ink">
              <TerminalSquare className="h-3.5 w-3.5 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
              <span>Pydantic v2 Schema Validation</span>
            </div>
            <span
              className={`font-mono text-[11px] font-semibold ${
                !candidate.schema_result.applicable
                  ? "text-muted"
                  : candidate.schema_result.schema_valid
                    ? "text-forest"
                    : "text-crimson"
              }`}
            >
              {!candidate.schema_result.applicable
                ? "NOT APPLICABLE"
                : candidate.schema_result.schema_valid
                  ? "VALID"
                  : "INVALID"}
            </span>
          </div>

          {!candidate.schema_result.applicable ? (
            <p className="text-muted">No strict JSON schema contract attached to this case.</p>
          ) : candidate.schema_result.schema_valid ? (
            <p className="text-forest [overflow-wrap:anywhere]">
              All required fields ({evalCase.schema_contract?.required_fields.join(", ")}) and
              type/bound constraints validated cleanly.
            </p>
          ) : (
            <div className="min-w-0 space-y-1.5 text-crimson">
              {candidate.schema_result.missing_fields.length > 0 && (
                <div className="font-mono text-[11px] [overflow-wrap:anywhere]">
                  Missing fields: {candidate.schema_result.missing_fields.join(", ")}
                </div>
              )}
              <ul className="list-disc space-y-0.5 pl-4 text-xs">
                {candidate.schema_result.constraint_violations.map((v, i) => (
                  <li key={i} className="[overflow-wrap:anywhere]">
                    {v}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="min-w-0 border border-rule bg-surface p-3.5">
          <div className="mb-2 flex items-center justify-between gap-2 border-b border-rule pb-2">
            <div className="flex items-center gap-1.5 font-serif text-xs font-bold text-ink">
              <GitBranch className="h-3.5 w-3.5 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
              <span>Tool-Call Sequence &amp; Arguments</span>
            </div>
            <span className="font-mono text-[11px] text-muted">
              {candidate.tool_result.applicable
                ? `F1=${candidate.tool_result.tool_f1.toFixed(2)} (P=${candidate.tool_result.tool_precision.toFixed(
                    2,
                  )}, R=${candidate.tool_result.tool_recall.toFixed(2)})`
                : "NO TOOLS EXPECTED"}
            </span>
          </div>

          {!candidate.tool_result.applicable ? (
            <p className="text-muted">Pure retrieval/grounding case with no expected tool calls.</p>
          ) : (
            <div className="min-w-0 space-y-2">
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="min-w-0">
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
                    Expected Sequence
                  </div>
                  <ol className="space-y-1 font-mono text-[11px]">
                    {evalCase.expected_tools.map((t, idx) => (
                      <li
                        key={idx}
                        className="border border-rule bg-inset/60 px-2 py-1 break-all [overflow-wrap:anywhere]"
                      >
                        {idx + 1}. {t.name}({JSON.stringify(t.required_args)})
                      </li>
                    ))}
                  </ol>
                </div>
                <div className="min-w-0">
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">
                    Candidate Sequence
                  </div>
                  <ol className="space-y-1 font-mono text-[11px]">
                    {candidate.predicted_tools.length === 0 ? (
                      <li className="border border-crimson/30 bg-[#FEF2F2] px-2 py-1 text-crimson break-all [overflow-wrap:anywhere]">
                        No tool calls emitted
                      </li>
                    ) : (
                      candidate.predicted_tools.map((t, idx) => (
                        <li
                          key={idx}
                          className={`border px-2 py-1 break-all [overflow-wrap:anywhere] ${
                            candidate.tool_result.tool_f1 >= 0.99
                              ? "border-forest/30 bg-[#ECFDF5] text-ink"
                              : "border-burgundy/30 bg-[#FDF2F4] text-ink"
                          }`}
                        >
                          {idx + 1}. {t.name}({JSON.stringify(t.args)})
                        </li>
                      ))
                    )}
                  </ol>
                </div>
              </div>
              {candidate.tool_result.violations.length > 0 && (
                <ul className="list-disc space-y-0.5 pl-4 text-xs text-crimson">
                  {candidate.tool_result.violations.map((v, i) => (
                    <li key={i} className="[overflow-wrap:anywhere]">
                      {v}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
