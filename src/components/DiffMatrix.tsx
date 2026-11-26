import React, { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import type { CaseDiffItem, DiffStatus } from "../types";
import { CaseInspector } from "./CaseInspector";

function useIsSmUp(): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== "undefined" ? window.matchMedia("(min-width: 640px)").matches : true,
  );
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    setMatches(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return matches;
}

export type DiffFilter = "all" | "regressions" | "failed" | "improved";

interface DiffMatrixProps {
  cases: CaseDiffItem[];
  counts: {
    all: number;
    regressions: number;
    failed: number;
    improved: number;
    passed: number;
  };
}

function statusBadgeStyle(status: DiffStatus): string {
  switch (status) {
    case "REGRESSION":
      return "border-burgundy/40 bg-[#FDF2F4] text-burgundy";
    case "FAILED":
      return "border-crimson/40 bg-[#FEF2F2] text-crimson";
    case "IMPROVED":
      return "border-forest/40 bg-[#ECFDF5] text-forest";
    case "PASSED":
      return "border-rule bg-inset text-muted";
  }
}

function formatMiniDelta(val: number, decimals: number = 3): string {
  if (Math.abs(val) < 0.0005) return "0.000";
  const sign = val > 0 ? "+" : "-";
  return `${sign}${Math.abs(val).toFixed(decimals)}`;
}

export const DiffMatrix: React.FC<DiffMatrixProps> = ({ cases, counts }) => {
  const isSmUp = useIsSmUp();
  const [filter, setFilter] = useState<DiffFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const toggleExpanded = (caseId: string) => {
    setExpandedIds((prev) => ({ ...prev, [caseId]: !prev[caseId] }));
  };

  const filteredCases = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    return cases.filter((item) => {
      if (filter === "regressions" && item.diff_status !== "REGRESSION") return false;
      if (filter === "failed" && item.candidate.passed) return false;
      if (filter === "improved" && item.diff_status !== "IMPROVED") return false;
      if (!q) return true;
      return (
        item.case.case_code.toLowerCase().includes(q) ||
        item.case.title.toLowerCase().includes(q) ||
        item.case.query.toLowerCase().includes(q) ||
        item.case.category.toLowerCase().includes(q) ||
        item.candidate.retrieved_doc_ids.some((id) => id.toLowerCase().includes(q))
      );
    });
  }, [cases, filter, searchTerm]);

  const filterTabs: { id: DiffFilter; label: string; count: number }[] = [
    { id: "all", label: "All", count: counts.all },
    { id: "regressions", label: "Regressions", count: counts.regressions },
    { id: "failed", label: "Failed", count: counts.failed },
    { id: "improved", label: "Improved", count: counts.improved },
  ];

  return (
    <section aria-labelledby="diff-matrix-heading" className="mt-6 space-y-3">
      <div className="flex flex-col gap-3 border-b border-rule pb-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="diff-matrix-heading" className="font-serif text-lg font-bold text-ink">
            Per-Case Regression Diff Matrix
          </h2>
          <p className="text-xs text-muted">
            Select any test case row to inspect side-by-side output diffs, ranked document IDs, atomic
            claim grounding, and schema traces.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search
            className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted"
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <input
            type="search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter code, title, or doc ID..."
            aria-label="Filter test cases"
            className="w-full border border-rule bg-surface py-1.5 pl-8 pr-3 text-xs text-ink placeholder:text-muted/70"
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div
        role="tablist"
        aria-label="Case status filter"
        className="flex flex-wrap items-center gap-1 border-b border-rule"
      >
        {filterTabs.map((tab) => {
          const active = filter === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setFilter(tab.id)}
              className={`-mb-px inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs transition-colors ${
                active
                  ? "border-burgundy font-semibold text-burgundy"
                  : "border-transparent font-medium text-muted hover:text-ink"
              }`}
            >
              <span>{tab.label}</span>
              <span className="font-mono text-[11px]">({tab.count})</span>
            </button>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredCases.length === 0 ? (
        <div className="border border-rule bg-surface p-8 text-center">
          <p className="font-serif text-sm font-semibold text-ink">
            No test cases match the current filter.
          </p>
          <p className="mt-1 text-xs text-muted">
            Try switching back to All or clearing the search query.
          </p>
        </div>
      ) : !isSmUp ? (
        /* Mobile Stacked Ledger Rows (<640px) — Zero Horizontal Overflow at 375px */
        <div className="divide-y divide-rule border border-rule bg-surface">
            {filteredCases.map((item) => {
              const isOpen = Boolean(expandedIds[item.case.id]);
              return (
                <div key={item.case.id}>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    onClick={() => toggleExpanded(item.case.id)}
                    className="w-full p-3.5 text-left transition-colors hover:bg-inset/40"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 min-w-0">
                        {isOpen ? (
                          <ChevronDown
                            className="mt-0.5 h-4 w-4 shrink-0 text-burgundy"
                            strokeWidth={1.75}
                            aria-hidden="true"
                          />
                        ) : (
                          <ChevronRight
                            className="mt-0.5 h-4 w-4 shrink-0 text-muted"
                            strokeWidth={1.75}
                            aria-hidden="true"
                          />
                        )}
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="font-mono text-xs font-semibold text-ink">
                              {item.case.case_code}
                            </span>
                            <span className="font-mono text-[10px] uppercase text-muted">
                              {item.case.category}
                            </span>
                          </div>
                          <div className="mt-0.5 text-xs font-semibold leading-snug text-ink">
                            {item.case.title}
                          </div>
                        </div>
                      </div>
                      <span
                        className={`shrink-0 border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${statusBadgeStyle(
                          item.diff_status,
                        )}`}
                      >
                        {item.diff_status}
                      </span>
                    </div>

                    <div className="mt-2.5 grid grid-cols-3 gap-2 border-t border-rule/70 pt-2 font-mono text-[11px]">
                      <div>
                        <span className="block text-[10px] text-muted">NDCG@5</span>
                        <span className="font-semibold text-ink">
                          {item.candidate.ndcg_at_5.toFixed(3)}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-muted">Faith</span>
                        <span className="font-semibold text-ink">
                          {item.candidate.faithfulness_score.toFixed(3)}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-muted">Schema</span>
                        <span
                          className={`font-semibold ${
                            !item.candidate.schema_result.applicable
                              ? "text-muted"
                              : item.candidate.schema_result.schema_valid
                                ? "text-forest"
                                : "text-crimson"
                          }`}
                        >
                          {!item.candidate.schema_result.applicable
                            ? "N/A"
                            : item.candidate.schema_result.schema_valid
                              ? "VALID"
                              : "FAIL"}
                        </span>
                      </div>
                    </div>
                  </button>
                  {isOpen && <CaseInspector item={item} />}
                </div>
              );
            })}
          </div>
      ) : (
        /* Desktop & Tablet Tabular Matrix (sm and up) */
        <div className="overflow-x-auto border border-rule bg-surface">
            <table className="w-full min-w-[740px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-rule bg-inset/70 text-[11px] font-semibold uppercase tracking-wider text-muted">
                  <th scope="col" className="px-3.5 py-2.5">
                    Golden Test Case
                  </th>
                  <th scope="col" className="px-3 py-2.5">
                    Diff Status
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right">
                    NDCG@5
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right">
                    Faithfulness
                  </th>
                  <th scope="col" className="px-3 py-2.5">
                    Schema
                  </th>
                  <th scope="col" className="px-3 py-2.5 text-right">
                    Tool F1
                  </th>
                  <th scope="col" className="px-3.5 py-2.5 text-right">
                    Latency
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-rule">
                {filteredCases.map((item) => {
                  const isOpen = Boolean(expandedIds[item.case.id]);
                  const dNdcg = item.deltas.ndcg_at_5;
                  const dFaith = item.deltas.faithfulness;

                  return (
                    <React.Fragment key={item.case.id}>
                      <tr
                        className={`transition-colors ${
                          isOpen ? "bg-inset/50" : "hover:bg-inset/30"
                        }`}
                      >
                        <td className="px-3.5 py-2.5">
                          <button
                            type="button"
                            aria-expanded={isOpen}
                            onClick={() => toggleExpanded(item.case.id)}
                            className="flex w-full items-start gap-2 text-left"
                          >
                            {isOpen ? (
                              <ChevronDown
                                className="mt-0.5 h-4 w-4 shrink-0 text-burgundy"
                                strokeWidth={1.75}
                                aria-hidden="true"
                              />
                            ) : (
                              <ChevronRight
                                className="mt-0.5 h-4 w-4 shrink-0 text-muted"
                                strokeWidth={1.75}
                                aria-hidden="true"
                              />
                            )}
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-semibold text-ink">
                                  {item.case.case_code}
                                </span>
                                <span className="font-semibold text-ink">{item.case.title}</span>
                              </div>
                              <div className="mt-0.5 line-clamp-1 text-[11px] text-muted">
                                {item.case.query}
                              </div>
                            </div>
                          </button>
                        </td>

                        <td className="whitespace-nowrap px-3 py-2.5">
                          <span
                            className={`inline-block border px-2 py-0.5 font-mono text-[10px] font-semibold ${statusBadgeStyle(
                              item.diff_status,
                            )}`}
                          >
                            {item.diff_status}
                          </span>
                        </td>

                        <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono">
                          <div className="font-semibold text-ink">
                            {item.candidate.ndcg_at_5.toFixed(3)}
                          </div>
                          <div
                            className={`text-[11px] ${
                              dNdcg > 0.001
                                ? "text-forest"
                                : dNdcg < -0.001
                                  ? "text-burgundy"
                                  : "text-muted"
                            }`}
                          >
                            {formatMiniDelta(dNdcg, 3)}
                          </div>
                        </td>

                        <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono">
                          <div className="font-semibold text-ink">
                            {item.candidate.faithfulness_score.toFixed(3)}
                          </div>
                          <div
                            className={`text-[11px] ${
                              dFaith > 0.001
                                ? "text-forest"
                                : dFaith < -0.001
                                  ? "text-burgundy"
                                  : "text-muted"
                            }`}
                          >
                            {formatMiniDelta(dFaith, 3)}
                          </div>
                        </td>

                        <td className="whitespace-nowrap px-3 py-2.5 font-mono">
                          {!item.candidate.schema_result.applicable ? (
                            <span className="text-muted">N/A</span>
                          ) : item.candidate.schema_result.schema_valid ? (
                            <span className="font-semibold text-forest">VALID</span>
                          ) : (
                            <span className="font-semibold text-crimson">INVALID</span>
                          )}
                        </td>

                        <td className="whitespace-nowrap px-3 py-2.5 text-right font-mono">
                          {item.candidate.tool_result.applicable ? (
                            <div>
                              <div className="font-semibold text-ink">
                                {item.candidate.tool_result.tool_f1.toFixed(2)}
                              </div>
                              <div
                                className={`text-[11px] ${
                                  item.deltas.tool_f1 > 0.001
                                    ? "text-forest"
                                    : item.deltas.tool_f1 < -0.001
                                      ? "text-burgundy"
                                      : "text-muted"
                                }`}
                              >
                                {formatMiniDelta(item.deltas.tool_f1, 2)}
                              </div>
                            </div>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>

                        <td className="whitespace-nowrap px-3.5 py-2.5 text-right font-mono">
                          <div className="text-ink">{item.candidate.latency_ms.toFixed(0)}ms</div>
                          <div className="text-[11px] text-muted">
                            {item.deltas.latency_ms >= 0 ? "+" : ""}
                            {item.deltas.latency_ms.toFixed(0)}ms
                          </div>
                        </td>
                      </tr>

                      {isOpen && (
                        <tr>
                          <td colSpan={7} className="p-0">
                            <CaseInspector item={item} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
      )}
    </section>
  );
};
