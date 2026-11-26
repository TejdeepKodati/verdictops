"""SQLite persistence layer for VerdictOps with Vercel /tmp automatic fallback."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from backend.models import (
    AtomicClaimTrace,
    CaseResult,
    CorpusPassage,
    EvalCase,
    EvalCaseCreate,
    EvalRun,
    EvalSuite,
    ExpectedToolCall,
    GatePolicy,
    GatePolicyUpdate,
    PredictedToolCall,
    RunSummaryMetrics,
    SchemaContract,
    SchemaValidationResult,
    ToolEvaluationResult,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_db_path() -> Path:
    """Resolve writable SQLite path.

    Uses VERDICT_DB_PATH if set, /tmp/verdictops.db on Vercel or read-only filesystems,
    and ./data/verdictops.db for local writable environments.
    """
    explicit = os.environ.get("VERDICT_DB_PATH")
    if explicit:
        target = Path(explicit)
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        return Path("/tmp/verdictops.db")

    local_dir = Path.cwd() / "data"
    try:
        local_dir.mkdir(parents=True, exist_ok=True)
        probe = local_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return local_dir / "verdictops.db"
    except OSError:
        return Path(tempfile.gettempdir()) / "verdictops.db"


class VerdictStore:
    """Thread-safe SQLite store managing suites, golden cases, runs, results, and gate policies."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else resolve_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS eval_suites (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subtitle TEXT NOT NULL,
                    description TEXT NOT NULL,
                    primary_focus TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS gate_policies (
                    suite_id TEXT PRIMARY KEY REFERENCES eval_suites(id) ON DELETE CASCADE,
                    min_ndcg REAL NOT NULL DEFAULT 0.75,
                    min_faithfulness REAL NOT NULL DEFAULT 0.80,
                    min_schema_pass REAL NOT NULL DEFAULT 0.90,
                    min_tool_f1 REAL NOT NULL DEFAULT 0.75,
                    max_ndcg_drop REAL NOT NULL DEFAULT 0.05,
                    max_faithfulness_drop REAL NOT NULL DEFAULT 0.05,
                    max_p95_latency_ms REAL NOT NULL DEFAULT 600.0
                );

                CREATE TABLE IF NOT EXISTS eval_cases (
                    id TEXT PRIMARY KEY,
                    suite_id TEXT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
                    case_code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    query TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'custom',
                    corpus_passages TEXT NOT NULL DEFAULT '[]',
                    relevant_docs TEXT NOT NULL DEFAULT '{}',
                    expected_claims TEXT NOT NULL DEFAULT '[]',
                    forbidden_claims TEXT NOT NULL DEFAULT '[]',
                    expected_tools TEXT NOT NULL DEFAULT '[]',
                    schema_contract TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE (suite_id, case_code)
                );

                CREATE TABLE IF NOT EXISTS eval_runs (
                    id TEXT PRIMARY KEY,
                    suite_id TEXT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    pipeline TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    is_baseline INTEGER NOT NULL DEFAULT 0,
                    config TEXT NOT NULL DEFAULT '{}',
                    metrics TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS case_results (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
                    case_id TEXT NOT NULL REFERENCES eval_cases(id) ON DELETE CASCADE,
                    case_code TEXT NOT NULL,
                    predicted_output TEXT NOT NULL,
                    retrieved_doc_ids TEXT NOT NULL DEFAULT '[]',
                    predicted_tools TEXT NOT NULL DEFAULT '[]',
                    ndcg_at_5 REAL NOT NULL DEFAULT 0.0,
                    mrr REAL NOT NULL DEFAULT 0.0,
                    recall_at_5 REAL NOT NULL DEFAULT 0.0,
                    precision_at_5 REAL NOT NULL DEFAULT 0.0,
                    faithfulness_score REAL NOT NULL DEFAULT 0.0,
                    claim_traces TEXT NOT NULL DEFAULT '[]',
                    forbidden_hits TEXT NOT NULL DEFAULT '[]',
                    schema_result TEXT NOT NULL,
                    tool_result TEXT NOT NULL,
                    latency_ms REAL NOT NULL DEFAULT 0.0,
                    passed INTEGER NOT NULL DEFAULT 1,
                    failure_reasons TEXT NOT NULL DEFAULT '[]',
                    judge_mode TEXT NOT NULL DEFAULT 'deterministic',
                    llm_judge_score REAL,
                    llm_judge_rationale TEXT,
                    UNIQUE (run_id, case_id)
                );

                CREATE INDEX IF NOT EXISTS idx_cases_suite ON eval_cases(suite_id);
                CREATE INDEX IF NOT EXISTS idx_runs_suite ON eval_runs(suite_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_results_run ON case_results(run_id);
                """
            )

    def has_suites(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM eval_suites").fetchone()
            return bool(row and row["cnt"] > 0)

    def upsert_suite(
        self,
        suite_id: str,
        name: str,
        subtitle: str,
        description: str,
        primary_focus: str,
        policy: GatePolicy,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_suites (id, name, subtitle, description, primary_focus, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    subtitle = excluded.subtitle,
                    description = excluded.description,
                    primary_focus = excluded.primary_focus
                """,
                (suite_id, name, subtitle, description, primary_focus, utc_now_iso()),
            )
            conn.execute(
                """
                INSERT INTO gate_policies (
                    suite_id, min_ndcg, min_faithfulness, min_schema_pass,
                    min_tool_f1, max_ndcg_drop, max_faithfulness_drop, max_p95_latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(suite_id) DO NOTHING
                """,
                (
                    suite_id,
                    policy.min_ndcg,
                    policy.min_faithfulness,
                    policy.min_schema_pass,
                    policy.min_tool_f1,
                    policy.max_ndcg_drop,
                    policy.max_faithfulness_drop,
                    policy.max_p95_latency_ms,
                ),
            )

    def list_suites(self) -> list[EvalSuite]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.*, gp.min_ndcg, gp.min_faithfulness, gp.min_schema_pass,
                       gp.min_tool_f1, gp.max_ndcg_drop, gp.max_faithfulness_drop,
                       gp.max_p95_latency_ms,
                       (SELECT COUNT(*) FROM eval_cases c WHERE c.suite_id = s.id) AS case_count
                FROM eval_suites s
                LEFT JOIN gate_policies gp ON gp.suite_id = s.id
                ORDER BY CASE s.id
                    WHEN 'rag-grounding' THEN 1
                    WHEN 'hybrid-retrieval' THEN 2
                    WHEN 'tool-schema' THEN 3
                    ELSE 4
                END, s.created_at ASC
                """
            ).fetchall()
            return [self._row_to_suite(r) for r in rows]

    def get_suite(self, suite_id: str) -> EvalSuite | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*, gp.min_ndcg, gp.min_faithfulness, gp.min_schema_pass,
                       gp.min_tool_f1, gp.max_ndcg_drop, gp.max_faithfulness_drop,
                       gp.max_p95_latency_ms,
                       (SELECT COUNT(*) FROM eval_cases c WHERE c.suite_id = s.id) AS case_count
                FROM eval_suites s
                LEFT JOIN gate_policies gp ON gp.suite_id = s.id
                WHERE s.id = ?
                """,
                (suite_id,),
            ).fetchone()
            return self._row_to_suite(row) if row else None

    def update_gate_policy(self, suite_id: str, update: GatePolicyUpdate) -> GatePolicy | None:
        if not self.get_suite(suite_id):
            return None
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE gate_policies
                SET min_ndcg = ?, min_faithfulness = ?, min_schema_pass = ?,
                    min_tool_f1 = ?, max_ndcg_drop = ?, max_faithfulness_drop = ?,
                    max_p95_latency_ms = ?
                WHERE suite_id = ?
                """,
                (
                    update.min_ndcg,
                    update.min_faithfulness,
                    update.min_schema_pass,
                    update.min_tool_f1,
                    update.max_ndcg_drop,
                    update.max_faithfulness_drop,
                    update.max_p95_latency_ms,
                    suite_id,
                ),
            )
        return GatePolicy(suite_id=suite_id, **update.model_dump())

    def add_case(self, suite_id: str, payload: EvalCaseCreate, case_id: str | None = None) -> EvalCase:
        with self._connect() as conn:
            existing_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM eval_cases WHERE suite_id = ?", (suite_id,)
            ).fetchone()["cnt"]
            prefix_map = {
                "rag-grounding": "RG",
                "hybrid-retrieval": "HR",
                "tool-schema": "TS",
            }
            prefix = prefix_map.get(suite_id, "CS")
            code = payload.case_code or f"{prefix}-{existing_count + 1:02d}"
            # Ensure unique case_code within suite
            suffix = 1
            base_code = code
            while conn.execute(
                "SELECT 1 FROM eval_cases WHERE suite_id = ? AND case_code = ?", (suite_id, code)
            ).fetchone():
                suffix += 1
                code = f"{base_code}-{suffix}"

            cid = case_id or f"case-{uuid.uuid4().hex[:10]}"
            now = utc_now_iso()
            conn.execute(
                """
                INSERT INTO eval_cases (
                    id, suite_id, case_code, title, query, category,
                    corpus_passages, relevant_docs, expected_claims,
                    forbidden_claims, expected_tools, schema_contract, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cid,
                    suite_id,
                    code,
                    payload.title,
                    payload.query,
                    payload.category,
                    json.dumps([p.model_dump() for p in payload.corpus_passages]),
                    json.dumps(payload.relevant_docs),
                    json.dumps(payload.expected_claims),
                    json.dumps(payload.forbidden_claims),
                    json.dumps([t.model_dump() for t in payload.expected_tools]),
                    json.dumps(payload.schema_contract.model_dump()) if payload.schema_contract else None,
                    now,
                ),
            )
        case = self.get_case(cid)
        assert case is not None
        return case

    def get_case(self, case_id: str) -> EvalCase | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM eval_cases WHERE id = ?", (case_id,)).fetchone()
            return self._row_to_case(row) if row else None

    def list_cases(self, suite_id: str) -> list[EvalCase]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_cases WHERE suite_id = ? ORDER BY case_code ASC",
                (suite_id,),
            ).fetchall()
            return [self._row_to_case(r) for r in rows]

    def save_run(self, run: EvalRun, results: list[CaseResult]) -> EvalRun:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_runs (
                    id, suite_id, name, pipeline, model_name, prompt_version,
                    is_baseline, config, metrics, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.suite_id,
                    run.name,
                    run.pipeline,
                    run.model_name,
                    run.prompt_version,
                    1 if run.is_baseline else 0,
                    json.dumps(run.config),
                    json.dumps(run.metrics.model_dump()),
                    run.created_at,
                ),
            )
            for res in results:
                conn.execute(
                    """
                    INSERT INTO case_results (
                        id, run_id, case_id, case_code, predicted_output,
                        retrieved_doc_ids, predicted_tools, ndcg_at_5, mrr,
                        recall_at_5, precision_at_5, faithfulness_score,
                        claim_traces, forbidden_hits, schema_result, tool_result,
                        latency_ms, passed, failure_reasons, judge_mode,
                        llm_judge_score, llm_judge_rationale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        res.id,
                        res.run_id,
                        res.case_id,
                        res.case_code,
                        res.predicted_output,
                        json.dumps(res.retrieved_doc_ids),
                        json.dumps([t.model_dump() for t in res.predicted_tools]),
                        res.ndcg_at_5,
                        res.mrr,
                        res.recall_at_5,
                        res.precision_at_5,
                        res.faithfulness_score,
                        json.dumps([c.model_dump() for c in res.claim_traces]),
                        json.dumps(res.forbidden_hits),
                        json.dumps(res.schema_result.model_dump()),
                        json.dumps(res.tool_result.model_dump()),
                        res.latency_ms,
                        1 if res.passed else 0,
                        json.dumps(res.failure_reasons),
                        res.judge_mode,
                        res.llm_judge_score,
                        res.llm_judge_rationale,
                    ),
                )
        return run

    def list_runs(self, suite_id: str) -> list[EvalRun]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM eval_runs WHERE suite_id = ? ORDER BY created_at ASC, rowid ASC",
                (suite_id,),
            ).fetchall()
            return [self._row_to_run(r) for r in rows]

    def get_run(self, run_id: str) -> EvalRun | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,)).fetchone()
            return self._row_to_run(row) if row else None

    def get_run_results(self, run_id: str) -> list[CaseResult]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM case_results WHERE run_id = ? ORDER BY case_code ASC",
                (run_id,),
            ).fetchall()
            return [self._row_to_case_result(r) for r in rows]

    @staticmethod
    def _row_to_suite(row: sqlite3.Row) -> EvalSuite:
        policy = GatePolicy(
            suite_id=row["id"],
            min_ndcg=row["min_ndcg"] if row["min_ndcg"] is not None else 0.75,
            min_faithfulness=row["min_faithfulness"] if row["min_faithfulness"] is not None else 0.80,
            min_schema_pass=row["min_schema_pass"] if row["min_schema_pass"] is not None else 0.90,
            min_tool_f1=row["min_tool_f1"] if row["min_tool_f1"] is not None else 0.75,
            max_ndcg_drop=row["max_ndcg_drop"] if row["max_ndcg_drop"] is not None else 0.05,
            max_faithfulness_drop=row["max_faithfulness_drop"] if row["max_faithfulness_drop"] is not None else 0.05,
            max_p95_latency_ms=row["max_p95_latency_ms"] if row["max_p95_latency_ms"] is not None else 600.0,
        )
        return EvalSuite(
            id=row["id"],
            name=row["name"],
            subtitle=row["subtitle"],
            description=row["description"],
            primary_focus=row["primary_focus"],
            case_count=int(row["case_count"]),
            gate_policy=policy,
        )

    @staticmethod
    def _row_to_case(row: sqlite3.Row) -> EvalCase:
        schema_raw = row["schema_contract"]
        return EvalCase(
            id=row["id"],
            suite_id=row["suite_id"],
            case_code=row["case_code"],
            title=row["title"],
            query=row["query"],
            category=row["category"],
            corpus_passages=[CorpusPassage(**p) for p in json.loads(row["corpus_passages"])],
            relevant_docs={k: float(v) for k, v in json.loads(row["relevant_docs"]).items()},
            expected_claims=json.loads(row["expected_claims"]),
            forbidden_claims=json.loads(row["forbidden_claims"]),
            expected_tools=[ExpectedToolCall(**t) for t in json.loads(row["expected_tools"])],
            schema_contract=SchemaContract(**json.loads(schema_raw)) if schema_raw else None,
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> EvalRun:
        return EvalRun(
            id=row["id"],
            suite_id=row["suite_id"],
            name=row["name"],
            pipeline=row["pipeline"],
            model_name=row["model_name"],
            prompt_version=row["prompt_version"],
            is_baseline=bool(row["is_baseline"]),
            config=json.loads(row["config"]),
            metrics=RunSummaryMetrics(**json.loads(row["metrics"])),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_case_result(row: sqlite3.Row) -> CaseResult:
        return CaseResult(
            id=row["id"],
            run_id=row["run_id"],
            case_id=row["case_id"],
            case_code=row["case_code"],
            predicted_output=row["predicted_output"],
            retrieved_doc_ids=json.loads(row["retrieved_doc_ids"]),
            predicted_tools=[PredictedToolCall(**t) for t in json.loads(row["predicted_tools"])],
            ndcg_at_5=float(row["ndcg_at_5"]),
            mrr=float(row["mrr"]),
            recall_at_5=float(row["recall_at_5"]),
            precision_at_5=float(row["precision_at_5"]),
            faithfulness_score=float(row["faithfulness_score"]),
            claim_traces=[AtomicClaimTrace(**c) for c in json.loads(row["claim_traces"])],
            forbidden_hits=json.loads(row["forbidden_hits"]),
            schema_result=SchemaValidationResult(**json.loads(row["schema_result"])),
            tool_result=ToolEvaluationResult(**json.loads(row["tool_result"])),
            latency_ms=float(row["latency_ms"]),
            passed=bool(row["passed"]),
            failure_reasons=json.loads(row["failure_reasons"]),
            judge_mode=row["judge_mode"],
            llm_judge_score=row["llm_judge_score"],
            llm_judge_rationale=row["llm_judge_rationale"],
        )
