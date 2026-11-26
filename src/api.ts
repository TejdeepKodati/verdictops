import type {
  ByokConfig,
  CompareResponse,
  EvalCase,
  EvalCaseCreate,
  EvalRun,
  EvalSuite,
  ExecuteRunRequest,
  ExecuteRunResponse,
  GatePolicy,
} from "./types";

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      if (errBody?.detail) {
        detail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore non-json error bodies
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function fetchSuites(): Promise<EvalSuite[]> {
  return requestJson<EvalSuite[]>("/api/suites");
}

export function fetchSuiteRuns(suiteId: string): Promise<EvalRun[]> {
  return requestJson<EvalRun[]>(`/api/suites/${encodeURIComponent(suiteId)}/runs`);
}

export function fetchCompare(
  suiteId: string,
  baselineId?: string,
  candidateId?: string,
): Promise<CompareResponse> {
  const params = new URLSearchParams({ suite_id: suiteId });
  if (baselineId) params.set("baseline_id", baselineId);
  if (candidateId) params.set("candidate_id", candidateId);
  return requestJson<CompareResponse>(`/api/compare?${params.toString()}`);
}

export function executeRun(
  payload: ExecuteRunRequest,
  byok?: ByokConfig,
): Promise<ExecuteRunResponse> {
  const extraHeaders: Record<string, string> = {};
  if (byok?.apiKey.trim()) {
    extraHeaders["X-LLM-Api-Key"] = byok.apiKey.trim();
    if (byok.baseUrl.trim()) extraHeaders["X-LLM-Base-Url"] = byok.baseUrl.trim();
    if (byok.model.trim()) extraHeaders["X-LLM-Model"] = byok.model.trim();
  }
  return requestJson<ExecuteRunResponse>("/api/runs/execute", {
    method: "POST",
    headers: extraHeaders,
    body: JSON.stringify(payload),
  });
}

export function createSuiteCase(
  suiteId: string,
  payload: EvalCaseCreate,
): Promise<EvalCase> {
  return requestJson<EvalCase>(`/api/suites/${encodeURIComponent(suiteId)}/cases`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateGatePolicy(
  suiteId: string,
  policy: Omit<GatePolicy, "suite_id">,
): Promise<GatePolicy> {
  return requestJson<GatePolicy>(`/api/suites/${encodeURIComponent(suiteId)}/gate-policy`, {
    method: "PUT",
    body: JSON.stringify(policy),
  });
}
