"""Pydantic v2 data models for VerdictOps evaluation suites, runs, metrics, and CI gates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ClaimVerdict = Literal["SUPPORTED", "PARTIAL", "UNSUPPORTED"]
DiffStatus = Literal["REGRESSION", "IMPROVED", "FAILED", "PASSED"]
GateVerdict = Literal["PASS", "FAIL"]
PipelinePreset = Literal[
    "bm25_only",
    "hybrid_rrf",
    "prompt_guardrailed",
    "prompt_unconstrained",
    "custom_weights",
]


class CorpusPassage(BaseModel):
    doc_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    relevance: float = Field(default=0.0, ge=0.0, le=3.0)


class ExpectedToolCall(BaseModel):
    name: str = Field(..., min_length=1)
    required_args: dict[str, Any] = Field(default_factory=dict)


class FieldConstraint(BaseModel):
    type: Literal["string", "integer", "number", "boolean", "array", "object"] = "string"
    required: bool = True
    enum: list[Any] | None = None
    min_value: float | None = None
    max_value: float | None = None
    min_length: int | None = None
    pattern: str | None = None


class SchemaContract(BaseModel):
    name: str = "StructuredResponse"
    required_fields: list[str] = Field(default_factory=list)
    fields: dict[str, FieldConstraint] = Field(default_factory=dict)


class EvalCaseCreate(BaseModel):
    case_code: str | None = None
    title: str = Field(..., min_length=3, max_length=180)
    query: str = Field(..., min_length=5)
    category: str = Field(default="custom", min_length=2, max_length=64)
    corpus_passages: list[CorpusPassage] = Field(default_factory=list)
    relevant_docs: dict[str, float] = Field(default_factory=dict)
    expected_claims: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    expected_tools: list[ExpectedToolCall] = Field(default_factory=list)
    schema_contract: SchemaContract | None = None

    @field_validator("relevant_docs")
    @classmethod
    def ensure_positive_weights(cls, v: dict[str, float]) -> dict[str, float]:
        return {k: float(val) for k, val in v.items() if float(val) >= 0.0}


class EvalCase(EvalCaseCreate):
    id: str
    suite_id: str
    case_code: str
    created_at: str


class GatePolicy(BaseModel):
    suite_id: str
    min_ndcg: float = Field(default=0.75, ge=0.0, le=1.0)
    min_faithfulness: float = Field(default=0.80, ge=0.0, le=1.0)
    min_schema_pass: float = Field(default=0.90, ge=0.0, le=1.0)
    min_tool_f1: float = Field(default=0.75, ge=0.0, le=1.0)
    max_ndcg_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_faithfulness_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_p95_latency_ms: float = Field(default=600.0, gt=0.0)


class GatePolicyUpdate(BaseModel):
    min_ndcg: float = Field(default=0.75, ge=0.0, le=1.0)
    min_faithfulness: float = Field(default=0.80, ge=0.0, le=1.0)
    min_schema_pass: float = Field(default=0.90, ge=0.0, le=1.0)
    min_tool_f1: float = Field(default=0.75, ge=0.0, le=1.0)
    max_ndcg_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_faithfulness_drop: float = Field(default=0.05, ge=0.0, le=1.0)
    max_p95_latency_ms: float = Field(default=600.0, gt=0.0)


class EvalSuite(BaseModel):
    id: str
    name: str
    subtitle: str
    description: str
    primary_focus: str
    case_count: int = 0
    gate_policy: GatePolicy


class AtomicClaimTrace(BaseModel):
    claim: str
    verdict: ClaimVerdict
    score: float
    matched_doc_id: str | None = None
    matched_passage_excerpt: str | None = None
    token_overlap: float = 0.0
    idf_bigram_similarity: float = 0.0
    numeric_mismatch: bool = False
    contradiction_detected: bool = False
    reason: str = ""


class SchemaValidationResult(BaseModel):
    applicable: bool = True
    schema_valid: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)


class ToolEvaluationResult(BaseModel):
    applicable: bool = False
    tool_precision: float = 1.0
    tool_recall: float = 1.0
    tool_f1: float = 1.0
    violations: list[str] = Field(default_factory=list)


class PredictedToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class CaseResult(BaseModel):
    id: str
    run_id: str
    case_id: str
    case_code: str
    predicted_output: str
    retrieved_doc_ids: list[str] = Field(default_factory=list)
    predicted_tools: list[PredictedToolCall] = Field(default_factory=list)
    ndcg_at_5: float = 0.0
    mrr: float = 0.0
    recall_at_5: float = 0.0
    precision_at_5: float = 0.0
    faithfulness_score: float = 0.0
    claim_traces: list[AtomicClaimTrace] = Field(default_factory=list)
    forbidden_hits: list[str] = Field(default_factory=list)
    schema_result: SchemaValidationResult = Field(default_factory=SchemaValidationResult)
    tool_result: ToolEvaluationResult = Field(default_factory=ToolEvaluationResult)
    latency_ms: float = 0.0
    passed: bool = True
    failure_reasons: list[str] = Field(default_factory=list)
    judge_mode: str = "deterministic"
    llm_judge_score: float | None = None
    llm_judge_rationale: str | None = None


class RunSummaryMetrics(BaseModel):
    ndcg_at_5: float
    mrr: float
    recall_at_5: float
    precision_at_5: float
    faithfulness: float
    schema_pass_rate: float
    tool_f1: float
    p95_latency_ms: float
    pass_rate: float
    total_cases: int
    passed_cases: int


class EvalRun(BaseModel):
    id: str
    suite_id: str
    name: str
    pipeline: str
    model_name: str
    prompt_version: str
    is_baseline: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    metrics: RunSummaryMetrics
    created_at: str


class ExecuteRunRequest(BaseModel):
    suite_id: str
    name: str | None = None
    pipeline: PipelinePreset = "hybrid_rrf"
    baseline_id: str | None = None
    model_name: str = "verdict-eval-engine-v2"
    prompt_version: str | None = None
    bm25_weight: float = Field(default=0.45, ge=0.0, le=1.0)
    dense_weight: float = Field(default=0.55, ge=0.0, le=1.0)
    guardrail_strictness: float = Field(default=0.9, ge=0.0, le=1.0)
    schema_enforcement: bool = True
    top_k: int = Field(default=5, ge=1, le=10)
    use_llm_judge: bool = False
    min_ndcg: float | None = Field(default=None, ge=0.0, le=1.0)
    min_faithfulness: float | None = Field(default=None, ge=0.0, le=1.0)
    min_schema_pass: float | None = Field(default=None, ge=0.0, le=1.0)
    max_ndcg_drop: float | None = Field(default=None, ge=0.0, le=1.0)


class ViolatedGateRule(BaseModel):
    rule: str
    label: str
    expected: str
    actual: str
    message: str


class MetricDeltas(BaseModel):
    ndcg_at_5: float
    mrr: float
    recall_at_5: float
    precision_at_5: float
    faithfulness: float
    schema_pass_rate: float
    tool_f1: float
    p95_latency_ms: float


class CaseDiffItem(BaseModel):
    case: EvalCase
    baseline: CaseResult
    candidate: CaseResult
    diff_status: DiffStatus
    deltas: dict[str, float]


class CompareResponse(BaseModel):
    suite: EvalSuite
    baseline_run: EvalRun
    candidate_run: EvalRun
    deltas: MetricDeltas
    gate_verdict: GateVerdict
    violated_rules: list[ViolatedGateRule]
    applied_policy: GatePolicy
    counts: dict[str, int]
    cases: list[CaseDiffItem]
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )


class ExecuteRunResponse(BaseModel):
    run: EvalRun
    comparison: CompareResponse | None = None
