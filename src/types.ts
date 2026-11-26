export type ClaimVerdict = "SUPPORTED" | "PARTIAL" | "UNSUPPORTED";
export type DiffStatus = "REGRESSION" | "IMPROVED" | "FAILED" | "PASSED";
export type GateVerdict = "PASS" | "FAIL";
export type PipelinePreset =
  | "bm25_only"
  | "hybrid_rrf"
  | "prompt_guardrailed"
  | "prompt_unconstrained"
  | "custom_weights";

export interface CorpusPassage {
  doc_id: string;
  title: string;
  text: string;
  relevance: number;
}

export interface ExpectedToolCall {
  name: string;
  required_args: Record<string, unknown>;
}

export interface FieldConstraint {
  type: "string" | "integer" | "number" | "boolean" | "array" | "object";
  required: boolean;
  enum?: unknown[] | null;
  min_value?: number | null;
  max_value?: number | null;
  min_length?: number | null;
  pattern?: string | null;
}

export interface SchemaContract {
  name: string;
  required_fields: string[];
  fields: Record<string, FieldConstraint>;
}

export interface EvalCase {
  id: string;
  suite_id: string;
  case_code: string;
  title: string;
  query: string;
  category: string;
  corpus_passages: CorpusPassage[];
  relevant_docs: Record<string, number>;
  expected_claims: string[];
  forbidden_claims: string[];
  expected_tools: ExpectedToolCall[];
  schema_contract: SchemaContract | null;
  created_at: string;
}

export interface EvalCaseCreate {
  case_code?: string;
  title: string;
  query: string;
  category: string;
  corpus_passages: CorpusPassage[];
  relevant_docs: Record<string, number>;
  expected_claims: string[];
  forbidden_claims: string[];
  expected_tools: ExpectedToolCall[];
  schema_contract: SchemaContract | null;
}

export interface GatePolicy {
  suite_id: string;
  min_ndcg: number;
  min_faithfulness: number;
  min_schema_pass: number;
  min_tool_f1: number;
  max_ndcg_drop: number;
  max_faithfulness_drop: number;
  max_p95_latency_ms: number;
}

export interface EvalSuite {
  id: string;
  name: string;
  subtitle: string;
  description: string;
  primary_focus: string;
  case_count: number;
  gate_policy: GatePolicy;
}

export interface AtomicClaimTrace {
  claim: string;
  verdict: ClaimVerdict;
  score: number;
  matched_doc_id: string | null;
  matched_passage_excerpt: string | null;
  token_overlap: number;
  idf_bigram_similarity: number;
  numeric_mismatch: boolean;
  contradiction_detected: boolean;
  reason: string;
}

export interface SchemaValidationResult {
  applicable: boolean;
  schema_valid: boolean;
  missing_fields: string[];
  constraint_violations: string[];
}

export interface ToolEvaluationResult {
  applicable: boolean;
  tool_precision: number;
  tool_recall: number;
  tool_f1: number;
  violations: string[];
}

export interface PredictedToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface CaseResult {
  id: string;
  run_id: string;
  case_id: string;
  case_code: string;
  predicted_output: string;
  retrieved_doc_ids: string[];
  predicted_tools: PredictedToolCall[];
  ndcg_at_5: number;
  mrr: number;
  recall_at_5: number;
  precision_at_5: number;
  faithfulness_score: number;
  claim_traces: AtomicClaimTrace[];
  forbidden_hits: string[];
  schema_result: SchemaValidationResult;
  tool_result: ToolEvaluationResult;
  latency_ms: number;
  passed: boolean;
  failure_reasons: string[];
  judge_mode: string;
  llm_judge_score: number | null;
  llm_judge_rationale: string | null;
}

export interface RunSummaryMetrics {
  ndcg_at_5: number;
  mrr: number;
  recall_at_5: number;
  precision_at_5: number;
  faithfulness: number;
  schema_pass_rate: number;
  tool_f1: number;
  p95_latency_ms: number;
  pass_rate: number;
  total_cases: number;
  passed_cases: number;
}

export interface EvalRun {
  id: string;
  suite_id: string;
  name: string;
  pipeline: string;
  model_name: string;
  prompt_version: string;
  is_baseline: boolean;
  config: Record<string, unknown>;
  metrics: RunSummaryMetrics;
  created_at: string;
}

export interface ViolatedGateRule {
  rule: string;
  label: string;
  expected: string;
  actual: string;
  message: string;
}

export interface MetricDeltas {
  ndcg_at_5: number;
  mrr: number;
  recall_at_5: number;
  precision_at_5: number;
  faithfulness: number;
  schema_pass_rate: number;
  tool_f1: number;
  p95_latency_ms: number;
}

export interface CaseDiffItem {
  case: EvalCase;
  baseline: CaseResult;
  candidate: CaseResult;
  diff_status: DiffStatus;
  deltas: {
    ndcg_at_5: number;
    faithfulness: number;
    tool_f1: number;
    latency_ms: number;
  };
}

export interface CompareResponse {
  suite: EvalSuite;
  baseline_run: EvalRun;
  candidate_run: EvalRun;
  deltas: MetricDeltas;
  gate_verdict: GateVerdict;
  violated_rules: ViolatedGateRule[];
  applied_policy: GatePolicy;
  counts: {
    all: number;
    regressions: number;
    failed: number;
    improved: number;
    passed: number;
  };
  cases: CaseDiffItem[];
  generated_at: string;
}

export interface ExecuteRunRequest {
  suite_id: string;
  name?: string;
  pipeline: PipelinePreset;
  baseline_id?: string;
  model_name?: string;
  prompt_version?: string;
  bm25_weight: number;
  dense_weight: number;
  guardrail_strictness: number;
  schema_enforcement: boolean;
  top_k: number;
  use_llm_judge: boolean;
}

export interface ExecuteRunResponse {
  run: EvalRun;
  comparison: CompareResponse | null;
}

export interface ByokConfig {
  apiKey: string;
  baseUrl: string;
  model: string;
}
