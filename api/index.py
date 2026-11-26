"""FastAPI application entrypoint for VerdictOps (Vercel serverless & local uvicorn compatible)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.evaluator import compare_runs, execute_live_sweep
from backend.models import (
    CompareResponse,
    EvalCase,
    EvalCaseCreate,
    EvalRun,
    EvalSuite,
    ExecuteRunRequest,
    ExecuteRunResponse,
    GatePolicy,
    GatePolicyUpdate,
)
from backend.seed import seed_if_empty
from backend.store import VerdictStore

_store_instance: VerdictStore | None = None


def get_store() -> VerdictStore:
    """Lazily initialize and seed VerdictStore (safe for Vercel serverless cold starts)."""
    global _store_instance
    if _store_instance is None:
        _store_instance = VerdictStore()
    seed_if_empty(_store_instance)
    return _store_instance


def reset_store_for_tests(store: VerdictStore) -> None:
    """Allow unit/integration tests to inject an isolated SQLite store."""
    global _store_instance
    _store_instance = store
    seed_if_empty(_store_instance)


app = FastAPI(
    title="VerdictOps Evaluation Harness API",
    version="1.0.0",
    description="Automated RAG & LLM Output Quality Evaluation Harness with Golden Datasets, IR Metrics, Faithfulness Scoring & CI Regression Gates.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    store = get_store()
    suites = store.list_suites()
    return {
        "status": "ok",
        "service": "verdictops",
        "db_path": str(store.db_path),
        "suite_count": len(suites),
        "total_cases": sum(s.case_count for s in suites),
    }


@app.get("/api/suites", response_model=list[EvalSuite])
def list_suites() -> list[EvalSuite]:
    store = get_store()
    return store.list_suites()


@app.get("/api/suites/{suite_id}")
def get_suite_detail(suite_id: str) -> dict[str, Any]:
    store = get_store()
    suite = store.get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")
    return {
        "suite": suite,
        "cases": store.list_cases(suite_id),
        "runs": store.list_runs(suite_id),
    }


@app.get("/api/suites/{suite_id}/cases", response_model=list[EvalCase])
def list_suite_cases(suite_id: str) -> list[EvalCase]:
    store = get_store()
    if not store.get_suite(suite_id):
        raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")
    return store.list_cases(suite_id)


@app.post("/api/suites/{suite_id}/cases", response_model=EvalCase, status_code=201)
def create_suite_case(suite_id: str, payload: EvalCaseCreate) -> EvalCase:
    store = get_store()
    if not store.get_suite(suite_id):
        raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")
    return store.add_case(suite_id, payload)


@app.put("/api/suites/{suite_id}/gate-policy", response_model=GatePolicy)
def update_gate_policy(suite_id: str, payload: GatePolicyUpdate) -> GatePolicy:
    store = get_store()
    updated = store.update_gate_policy(suite_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")
    return updated


@app.get("/api/suites/{suite_id}/runs", response_model=list[EvalRun])
def list_suite_runs(suite_id: str) -> list[EvalRun]:
    store = get_store()
    if not store.get_suite(suite_id):
        raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")
    return store.list_runs(suite_id)


@app.get("/api/runs/{run_id}")
def get_run_detail(run_id: str) -> dict[str, Any]:
    store = get_store()
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "run": run,
        "results": store.get_run_results(run_id),
    }


@app.post("/api/runs/execute", response_model=ExecuteRunResponse)
def execute_run(
    payload: ExecuteRunRequest,
    x_llm_api_key: str | None = Header(default=None),
    x_llm_base_url: str = Header(default="https://api.openai.com/v1"),
    x_llm_model: str = Header(default="gpt-4o-mini"),
) -> ExecuteRunResponse:
    store = get_store()
    try:
        run, _ = execute_live_sweep(
            store=store,
            req=payload,
            llm_api_key=x_llm_api_key,
            llm_base_url=x_llm_base_url,
            llm_model=x_llm_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    overrides: dict[str, float] = {}
    if payload.min_ndcg is not None:
        overrides["min_ndcg"] = payload.min_ndcg
    if payload.min_faithfulness is not None:
        overrides["min_faithfulness"] = payload.min_faithfulness
    if payload.min_schema_pass is not None:
        overrides["min_schema_pass"] = payload.min_schema_pass
    if payload.max_ndcg_drop is not None:
        overrides["max_ndcg_drop"] = payload.max_ndcg_drop

    comparison = compare_runs(
        store=store,
        suite_id=payload.suite_id,
        baseline_id=payload.baseline_id,
        candidate_id=run.id,
        policy_overrides=overrides or None,
    )
    return ExecuteRunResponse(run=run, comparison=comparison)


@app.get("/api/compare", response_model=CompareResponse)
def compare_suite_runs(
    suite_id: str = Query(...),
    baseline_id: str | None = Query(default=None),
    candidate_id: str | None = Query(default=None),
    min_ndcg: float | None = Query(default=None, ge=0.0, le=1.0),
    min_faithfulness: float | None = Query(default=None, ge=0.0, le=1.0),
    min_schema_pass: float | None = Query(default=None, ge=0.0, le=1.0),
    min_tool_f1: float | None = Query(default=None, ge=0.0, le=1.0),
    max_ndcg_drop: float | None = Query(default=None, ge=0.0, le=1.0),
) -> CompareResponse:
    store = get_store()
    overrides = {
        k: v
        for k, v in {
            "min_ndcg": min_ndcg,
            "min_faithfulness": min_faithfulness,
            "min_schema_pass": min_schema_pass,
            "min_tool_f1": min_tool_f1,
            "max_ndcg_drop": max_ndcg_drop,
        }.items()
        if v is not None
    }
    try:
        return compare_runs(
            store=store,
            suite_id=suite_id,
            baseline_id=baseline_id,
            candidate_id=candidate_id,
            policy_overrides=overrides or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


_dist_dir = Path(__file__).resolve().parent.parent / "dist"
if _dist_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="static-ui")
