import React, { useEffect, useState } from "react";
import {
  ChevronDown,
  FlaskConical,
  KeyRound,
  Layers,
  Play,
  Plus,
  Scale,
  X,
} from "lucide-react";
import type { ByokConfig, EvalRun, EvalSuite } from "../types";

function useIsLgUp(): boolean {
  const [matches, setMatches] = useState<boolean>(() =>
    typeof window !== "undefined" ? window.matchMedia("(min-width: 1024px)").matches : true,
  );
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    setMatches(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return matches;
}

interface SidebarProps {
  suites: EvalSuite[];
  selectedSuiteId: string;
  onSelectSuite: (suiteId: string) => void;
  runs: EvalRun[];
  baselineId: string;
  candidateId: string;
  onSelectBaseline: (runId: string) => void;
  onSelectCandidate: (runId: string) => void;
  onOpenRunSweep: () => void;
  onOpenAddCase: () => void;
  byok: ByokConfig;
  onChangeByok: (next: ByokConfig) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  suites,
  selectedSuiteId,
  onSelectSuite,
  runs,
  baselineId,
  candidateId,
  onSelectBaseline,
  onSelectCandidate,
  onOpenRunSweep,
  onOpenAddCase,
  byok,
  onChangeByok,
  mobileOpen,
  onCloseMobile,
}) => {
  const isLgUp = useIsLgUp();
  const [byokOpen, setByokOpen] = useState(false);

  const sidebarBody = (
    <div className="flex h-full flex-col justify-between bg-inset/60 text-ink">
      <div className="space-y-6 p-4">
        {/* Masthead Brand */}
        <div className="border-b border-rule pb-4">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center border border-burgundy/30 bg-surface text-burgundy">
                <Scale className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              </div>
              <div>
                <div className="font-serif text-lg font-bold tracking-tight text-ink">
                  VerdictOps
                </div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  Eval &amp; Gate Harness
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Close navigation drawer"
              className="inline-flex h-8 w-8 items-center justify-center border border-rule bg-surface text-ink lg:hidden"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        </div>

        {/* Suite Picker */}
        <section aria-labelledby="suites-heading">
          <div
            id="suites-heading"
            className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted"
          >
            <Layers className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span>Evaluation Suites</span>
          </div>
          <nav className="space-y-1.5" aria-label="Evaluation suites">
            {suites.map((suite) => {
              const active = suite.id === selectedSuiteId;
              return (
                <button
                  key={suite.id}
                  type="button"
                  onClick={() => {
                    onSelectSuite(suite.id);
                    onCloseMobile();
                  }}
                  aria-current={active ? "page" : undefined}
                  className={`w-full border text-left transition-colors px-3 py-2.5 ${
                    active
                      ? "border-rule border-l-[3px] border-l-burgundy bg-surface shadow-sm"
                      : "border-transparent bg-transparent hover:border-rule hover:bg-surface/70"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span
                      className={`font-serif text-sm leading-snug ${
                        active ? "font-bold text-ink" : "font-semibold text-ink/90"
                      }`}
                    >
                      {suite.name}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-muted">
                      {suite.case_count}
                    </span>
                  </div>
                  <div className="mt-1 text-[11px] text-muted">{suite.primary_focus}</div>
                </button>
              );
            })}
          </nav>
        </section>

        {/* Experiment Comparison Pair */}
        <section aria-labelledby="compare-pair-heading" className="border-t border-rule pt-4">
          <div
            id="compare-pair-heading"
            className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted"
          >
            <FlaskConical className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span>Experiment Comparison</span>
          </div>

          <div className="space-y-3">
            <div>
              <label
                htmlFor="baseline-run-select"
                className="mb-1 block text-xs font-medium text-muted"
              >
                Baseline Reference
              </label>
              <div className="relative">
                <select
                  id="baseline-run-select"
                  value={baselineId}
                  onChange={(e) => onSelectBaseline(e.target.value)}
                  className="w-full appearance-none border border-rule bg-surface py-2 pl-2.5 pr-8 text-xs font-medium text-ink"
                >
                  {runs.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  className="pointer-events-none absolute right-2.5 top-2.5 h-3.5 w-3.5 text-muted"
                  strokeWidth={1.75}
                  aria-hidden="true"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="candidate-run-select"
                className="mb-1 block text-xs font-medium text-muted"
              >
                Candidate Under Test
              </label>
              <div className="relative">
                <select
                  id="candidate-run-select"
                  value={candidateId}
                  onChange={(e) => onSelectCandidate(e.target.value)}
                  className="w-full appearance-none border border-rule bg-surface py-2 pl-2.5 pr-8 text-xs font-medium text-ink"
                >
                  {runs.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  className="pointer-events-none absolute right-2.5 top-2.5 h-3.5 w-3.5 text-muted"
                  strokeWidth={1.75}
                  aria-hidden="true"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Primary Execution Actions */}
        <section className="space-y-2 border-t border-rule pt-4">
          <button
            type="button"
            onClick={() => {
              onOpenRunSweep();
              onCloseMobile();
            }}
            className="flex w-full items-center justify-center gap-2 bg-burgundy px-3 py-2.5 text-xs font-semibold text-white transition-colors hover:bg-[#881337]"
          >
            <Play className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span>Run Live Eval Sweep</span>
          </button>

          <button
            type="button"
            onClick={() => {
              onOpenAddCase();
              onCloseMobile();
            }}
            className="flex w-full items-center justify-center gap-2 border border-rule bg-surface px-3 py-2 text-xs font-semibold text-ink transition-colors hover:bg-inset"
          >
            <Plus className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span>Add Golden Test Case</span>
          </button>
        </section>
      </div>

      {/* Optional BYOK LLM-as-a-Judge Configuration */}
      <div className="border-t border-rule p-4">
        <button
          type="button"
          onClick={() => setByokOpen((v) => !v)}
          aria-expanded={byokOpen}
          className="flex w-full items-center justify-between text-xs font-medium text-muted hover:text-ink"
        >
          <span className="flex items-center gap-1.5">
            <KeyRound className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            <span>BYOK LLM Judge</span>
          </span>
          <span className="font-mono text-[11px]">
            {byok.apiKey.trim() ? "SET" : "OFF"}
          </span>
        </button>

        {byokOpen && (
          <div className="mt-3 space-y-2 border border-rule bg-surface p-2.5 text-xs">
            <p className="text-[11px] leading-relaxed text-muted">
              Optional OpenAI-compatible key sent via{" "}
              <code className="font-mono text-[10px]">X-LLM-Api-Key</code> alongside deterministic scoring.
            </p>
            <div>
              <label htmlFor="byok-key" className="mb-1 block text-[11px] font-medium text-muted">
                API Key
              </label>
              <input
                id="byok-key"
                type="password"
                value={byok.apiKey}
                onChange={(e) => onChangeByok({ ...byok, apiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full border border-rule bg-canvas px-2 py-1.5 font-mono text-xs text-ink"
              />
            </div>
            <div>
              <label htmlFor="byok-model" className="mb-1 block text-[11px] font-medium text-muted">
                Judge Model
              </label>
              <input
                id="byok-model"
                type="text"
                value={byok.model}
                onChange={(e) => onChangeByok({ ...byok, model: e.target.value })}
                placeholder="gpt-4o-mini"
                className="w-full border border-rule bg-canvas px-2 py-1.5 font-mono text-xs text-ink"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (isLgUp) {
    return (
      <aside
        aria-label="Suite and Experiment Navigation"
        className="w-[260px] shrink-0 border-r border-rule bg-inset/50"
      >
        <div className="sticky top-0 h-screen overflow-y-auto">{sidebarBody}</div>
      </aside>
    );
  }

  if (!mobileOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex"
      role="dialog"
      aria-modal="true"
      aria-label="Suite and experiment controls"
    >
      <div
        className="fixed inset-0 bg-ink/40"
        onClick={onCloseMobile}
        aria-hidden="true"
      />
      <div className="relative z-10 h-full w-[280px] max-w-[85vw] overflow-y-auto border-r border-rule bg-canvas shadow-xl">
        {sidebarBody}
      </div>
    </div>
  );
};
