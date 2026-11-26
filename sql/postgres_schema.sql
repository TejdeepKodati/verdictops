-- VerdictOps Production PostgreSQL Schema
-- Matches the SQLite schema in backend/store.py for zero-friction production migration.

CREATE TABLE IF NOT EXISTS eval_suites (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    description TEXT NOT NULL,
    primary_focus TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gate_policies (
    suite_id TEXT PRIMARY KEY REFERENCES eval_suites(id) ON DELETE CASCADE,
    min_ndcg DOUBLE PRECISION NOT NULL DEFAULT 0.75,
    min_faithfulness DOUBLE PRECISION NOT NULL DEFAULT 0.80,
    min_schema_pass DOUBLE PRECISION NOT NULL DEFAULT 0.90,
    min_tool_f1 DOUBLE PRECISION NOT NULL DEFAULT 0.75,
    max_ndcg_drop DOUBLE PRECISION NOT NULL DEFAULT 0.05,
    max_faithfulness_drop DOUBLE PRECISION NOT NULL DEFAULT 0.05,
    max_p95_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 600.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS eval_cases (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    case_code TEXT NOT NULL,
    title TEXT NOT NULL,
    query TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'custom',
    corpus_passages JSONB NOT NULL DEFAULT '[]'::jsonb,
    relevant_docs JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    forbidden_claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    schema_contract JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (suite_id, case_code)
);

CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_id ON eval_cases(suite_id);

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    is_baseline BOOLEAN NOT NULL DEFAULT FALSE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_suite_created ON eval_runs(suite_id, created_at DESC);

CREATE TABLE IF NOT EXISTS case_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL REFERENCES eval_cases(id) ON DELETE CASCADE,
    case_code TEXT NOT NULL,
    predicted_output TEXT NOT NULL,
    retrieved_doc_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    predicted_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    ndcg_at_5 DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    mrr DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    recall_at_5 DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    precision_at_5 DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    faithfulness_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    claim_traces JSONB NOT NULL DEFAULT '[]'::jsonb,
    forbidden_hits JSONB NOT NULL DEFAULT '[]'::jsonb,
    schema_result JSONB NOT NULL,
    tool_result JSONB NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    passed BOOLEAN NOT NULL DEFAULT TRUE,
    failure_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    judge_mode TEXT NOT NULL DEFAULT 'deterministic',
    llm_judge_score DOUBLE PRECISION,
    llm_judge_rationale TEXT,
    UNIQUE (run_id, case_id)
);

CREATE INDEX IF NOT EXISTS idx_case_results_run_id ON case_results(run_id);
CREATE INDEX IF NOT EXISTS idx_case_results_case_id ON case_results(case_id);
