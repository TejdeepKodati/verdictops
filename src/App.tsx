import React, { useCallback, useEffect, useState } from "react";
import { Menu, Play, RefreshCw, Scale } from "lucide-react";
import {
  createSuiteCase,
  executeRun,
  fetchCompare,
  fetchSuiteRuns,
  fetchSuites,
  updateGatePolicy,
} from "./api";
import { AddCaseModal } from "./components/AddCaseModal";
import { Colophon } from "./components/Colophon";
import { DiffMatrix } from "./components/DiffMatrix";
import { LedgerStrip } from "./components/LedgerStrip";
import { RunSweepModal } from "./components/RunSweepModal";
import { Sidebar } from "./components/Sidebar";
import type {
  ByokConfig,
  CompareResponse,
  EvalCaseCreate,
  EvalRun,
  EvalSuite,
  ExecuteRunRequest,
  GatePolicy,
} from "./types";

export const App: React.FC = () => {
  const [suites, setSuites] = useState<EvalSuite[]>([]);
  const [selectedSuiteId, setSelectedSuiteId] = useState<string>("rag-grounding");
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [baselineId, setBaselineId] = useState<string>("");
  const [candidateId, setCandidateId] = useState<string>("");
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [addCaseModalOpen, setAddCaseModalOpen] = useState(false);

  const [byok, setByok] = useState<ByokConfig>({
    apiKey: "",
    baseUrl: "https://api.openai.com/v1",
    model: "gpt-4o-mini",
  });

  const loadComparison = useCallback(
    async (suiteId: string, baseId?: string, candId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const comp = await fetchCompare(suiteId, baseId, candId);
        setComparison(comp);
        setBaselineId(comp.baseline_run.id);
        setCandidateId(comp.candidate_run.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load evaluation comparison");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Initial bootstrap: load suites and first suite's runs + comparison
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const suiteList = await fetchSuites();
        if (cancelled) return;
        setSuites(suiteList);
        const initialSuite = suiteList[0]?.id ?? "rag-grounding";
        setSelectedSuiteId(initialSuite);
        const runList = await fetchSuiteRuns(initialSuite);
        if (cancelled) return;
        setRuns(runList);
        const defaultBase = runList.find((r) => r.is_baseline)?.id ?? runList[0]?.id;
        const defaultCand = runList[1]?.id ?? runList[0]?.id;
        await loadComparison(initialSuite, defaultBase, defaultCand);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to connect to VerdictOps API");
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadComparison]);

  const handleSelectSuite = async (suiteId: string) => {
    setSelectedSuiteId(suiteId);
    setLoading(true);
    setError(null);
    try {
      const runList = await fetchSuiteRuns(suiteId);
      setRuns(runList);
      const defaultBase = runList.find((r) => r.is_baseline)?.id ?? runList[0]?.id;
      const defaultCand = runList[1]?.id ?? runList[0]?.id;
      await loadComparison(suiteId, defaultBase, defaultCand);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to switch suite");
      setLoading(false);
    }
  };

  const handleSelectBaseline = async (nextBaseId: string) => {
    setBaselineId(nextBaseId);
    await loadComparison(selectedSuiteId, nextBaseId, candidateId);
  };

  const handleSelectCandidate = async (nextCandId: string) => {
    setCandidateId(nextCandId);
    await loadComparison(selectedSuiteId, baselineId, nextCandId);
  };

  const handleSavePolicy = async (policy: Omit<GatePolicy, "suite_id">) => {
    await updateGatePolicy(selectedSuiteId, policy);
    const updatedSuites = await fetchSuites();
    setSuites(updatedSuites);
    await loadComparison(selectedSuiteId, baselineId, candidateId);
    setToast("CI Gate Policy updated.");
    window.setTimeout(() => setToast(null), 2600);
  };

  const handleExecuteSweep = async (payload: ExecuteRunRequest) => {
    const res = await executeRun(payload, byok);
    const [updatedSuites, updatedRuns] = await Promise.all([
      fetchSuites(),
      fetchSuiteRuns(payload.suite_id),
    ]);
    setSuites(updatedSuites);
    setRuns(updatedRuns);
    if (res.comparison) {
      setComparison(res.comparison);
      setBaselineId(res.comparison.baseline_run.id);
      setCandidateId(res.comparison.candidate_run.id);
    } else {
      await loadComparison(payload.suite_id, payload.baseline_id ?? baselineId, res.run.id);
    }
    setToast(`Sweep '${res.run.name}' completed (${res.comparison?.gate_verdict ?? "DONE"}).`);
    window.setTimeout(() => setToast(null), 3200);
  };

  const handleCreateCase = async (payload: EvalCaseCreate, rerunAfterSave: boolean) => {
    const created = await createSuiteCase(selectedSuiteId, payload);
    const updatedSuites = await fetchSuites();
    setSuites(updatedSuites);

    if (rerunAfterSave) {
      await handleExecuteSweep({
        suite_id: selectedSuiteId,
        name: `Live Sweep (+${created.case_code})`,
        pipeline: "hybrid_rrf",
        baseline_id: baselineId,
        bm25_weight: 0.35,
        dense_weight: 0.65,
        guardrail_strictness: 0.94,
        schema_enforcement: true,
        top_k: 5,
        use_llm_judge: Boolean(byok.apiKey.trim()),
      });
    } else {
      await loadComparison(selectedSuiteId, baselineId, candidateId);
      setToast(`Added golden case ${created.case_code}. Run live sweep to score it.`);
      window.setTimeout(() => setToast(null), 3200);
    }
  };

  const activeSuite = suites.find((s) => s.id === selectedSuiteId);

  return (
    <div className="flex min-h-screen bg-canvas text-ink">
      <Sidebar
        suites={suites}
        selectedSuiteId={selectedSuiteId}
        onSelectSuite={handleSelectSuite}
        runs={runs}
        baselineId={baselineId}
        candidateId={candidateId}
        onSelectBaseline={handleSelectBaseline}
        onSelectCandidate={handleSelectCandidate}
        onOpenRunSweep={() => setRunModalOpen(true)}
        onOpenAddCase={() => setAddCaseModalOpen(true)}
        byok={byok}
        onChangeByok={setByok}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Compact Mobile Top Bar (< lg) */}
        <div className="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-rule bg-canvas/95 px-4 py-2.5 backdrop-blur lg:hidden">
          <div className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open suite navigation"
              className="inline-flex h-8 w-8 shrink-0 items-center justify-center border border-rule bg-surface text-ink"
            >
              <Menu className="h-4 w-4" strokeWidth={1.75} />
            </button>
            <div className="flex min-w-0 items-center gap-1.5">
              <Scale className="h-4 w-4 shrink-0 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
              <span className="truncate font-serif text-sm font-bold text-ink">VerdictOps</span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setRunModalOpen(true)}
            className="inline-flex shrink-0 items-center gap-1.5 bg-burgundy px-2.5 py-1.5 text-xs font-semibold text-white"
          >
            <Play className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
            <span>Run Sweep</span>
          </button>
        </div>

        {/* Main Analytical Broadsheet */}
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col justify-between px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <div>
            {toast && (
              <div
                role="status"
                className="mb-4 flex items-center justify-between border border-forest/30 bg-[#ECFDF5] px-3.5 py-2 text-xs font-medium text-forest"
              >
                <span>{toast}</span>
              </div>
            )}

            {error && (
              <div
                role="alert"
                className="mb-5 flex flex-wrap items-center justify-between gap-3 border border-crimson/40 bg-[#FEF2F2] px-4 py-3 text-xs text-crimson"
              >
                <span>{error}</span>
                <button
                  type="button"
                  onClick={() => loadComparison(selectedSuiteId, baselineId, candidateId)}
                  className="inline-flex items-center gap-1 border border-crimson/40 bg-surface px-2.5 py-1 font-semibold text-crimson"
                >
                  <RefreshCw className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
                  <span>Retry</span>
                </button>
              </div>
            )}

            {loading && !comparison ? (
              <div className="space-y-4 py-8">
                <div className="h-8 w-64 animate-pulse bg-inset" />
                <div className="h-24 w-full animate-pulse border border-rule bg-surface" />
                <div className="h-64 w-full animate-pulse border border-rule bg-surface" />
              </div>
            ) : comparison ? (
              <>
                <LedgerStrip comparison={comparison} onSavePolicy={handleSavePolicy} />
                <DiffMatrix
                  key={`${comparison.suite.id}:${comparison.candidate_run.id}`}
                  cases={comparison.cases}
                  counts={comparison.counts}
                />
              </>
            ) : null}
          </div>

          {/* Editorial Bottom Colophon with CLI snippet + required credit link */}
          <Colophon comparison={comparison} />
        </main>
      </div>

      <RunSweepModal
        open={runModalOpen}
        suiteId={selectedSuiteId}
        suiteName={activeSuite?.name ?? selectedSuiteId}
        runs={runs}
        defaultBaselineId={baselineId}
        byok={byok}
        onClose={() => setRunModalOpen(false)}
        onExecute={handleExecuteSweep}
      />

      <AddCaseModal
        open={addCaseModalOpen}
        suiteId={selectedSuiteId}
        suiteName={activeSuite?.name ?? selectedSuiteId}
        onClose={() => setAddCaseModalOpen(false)}
        onCreateCase={handleCreateCase}
      />
    </div>
  );
};

export default App;
