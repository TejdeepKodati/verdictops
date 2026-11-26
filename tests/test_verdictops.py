"""Comprehensive test suite for VerdictOps IR math, faithfulness, schemas, CLI, and FastAPI."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.index import app, reset_store_for_tests
from backend import cli
from backend.metrics import (
    evaluate_tool_calls,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    score_faithfulness,
    validate_structured_output,
)
from backend.models import (
    CorpusPassage,
    ExpectedToolCall,
    FieldConstraint,
    PredictedToolCall,
    SchemaContract,
)
from backend.store import VerdictStore, resolve_db_path


@pytest.fixture()
def isolated_store(tmp_path: Path) -> VerdictStore:
    db_file = tmp_path / "test_verdictops.db"
    store = VerdictStore(db_path=db_file)
    reset_store_for_tests(store)
    return store


def test_ir_metrics_match_hand_calculated_values() -> None:
    relevant = {"d1": 2.0, "d2": 1.0, "d3": 1.0}
    # Duplicate "d1" must be deduplicated cleanly so rank order is ["d1", "x1", "d3", "x2"]
    predicted = ["d1", "x1", "d3", "d1", "x2"]

    assert recall_at_k(predicted, relevant, k=5) == pytest.approx(2.0 / 3.0, abs=1e-4)
    assert precision_at_k(predicted, relevant, k=5) == pytest.approx(2.0 / 5.0, abs=1e-4)
    assert mrr(["x1", "d2", "d1"], relevant) == pytest.approx(0.5, abs=1e-4)
    assert mrr(["x1", "x2"], relevant) == 0.0

    # Hand-calculated graded NDCG@3:
    # predicted = ["d2" (rel=1), "d1" (rel=2), "x1" (rel=0)]
    dcg = (2**1 - 1) / math.log2(2) + (2**2 - 1) / math.log2(3) + 0.0
    idcg = (2**2 - 1) / math.log2(2) + (2**1 - 1) / math.log2(3)
    expected_ndcg = dcg / idcg
    assert ndcg_at_k(["d2", "d1", "x1"], {"d1": 2.0, "d2": 1.0}, k=3) == pytest.approx(
        expected_ndcg, abs=1e-4
    )
    assert ndcg_at_k(["d1", "d2"], {"d1": 2.0, "d2": 1.0}, k=3) == pytest.approx(1.0, abs=1e-4)


def test_faithfulness_catches_fabricated_numbers_and_contradictions() -> None:
    passages = [
        CorpusPassage(
            doc_id="DOC-1",
            title="Retention Spec",
            text="Audit logs remain in hot NVMe storage for 365 days and encryption is enabled by default.",
            relevance=2.0,
        )
    ]

    grounded_answer = "Audit logs stay in hot NVMe storage for 365 days [DOC-1]."
    score_ok, traces_ok, hits_ok = score_faithfulness(grounded_answer, passages)
    assert score_ok == pytest.approx(1.0, abs=1e-4)
    assert traces_ok[0].verdict == "SUPPORTED"
    assert not hits_ok

    hallucinated_answer = (
        "Audit logs stay in hot NVMe storage for 90 days and customers receive $500 penalties."
    )
    score_bad, traces_bad, _ = score_faithfulness(hallucinated_answer, passages)
    assert score_bad < 0.5
    assert any(t.verdict == "UNSUPPORTED" and t.numeric_mismatch for t in traces_bad)

    contradiction_answer = "Encryption is disabled and not supported for audit logs."
    score_contra, traces_contra, _ = score_faithfulness(contradiction_answer, passages)
    assert score_contra == 0.0
    assert traces_contra[0].verdict == "UNSUPPORTED"
    assert traces_contra[0].contradiction_detected is True


def test_pydantic_schema_validation_enforces_strict_json_and_constraints() -> None:
    contract = SchemaContract(
        name="RefundDecision",
        required_fields=["decision", "amount_usd", "citations"],
        fields={
            "decision": FieldConstraint(type="string", enum=["approved", "denied"]),
            "amount_usd": FieldConstraint(type="number", min_value=0.0, max_value=500.0),
            "citations": FieldConstraint(type="array", min_length=1),
        },
    )

    valid_json = json.dumps({"decision": "approved", "amount_usd": 240, "citations": ["DOC-1"]})
    res_ok = validate_structured_output(valid_json, contract)
    assert res_ok.schema_valid is True
    assert res_ok.missing_fields == []
    assert res_ok.constraint_violations == []

    wrapped = f"Here is the output:\n```json\n{valid_json}\n```"
    res_wrapped = validate_structured_output(wrapped, contract)
    assert res_wrapped.schema_valid is False
    assert any("markdown" in v.lower() or "valid json" in v.lower() for v in res_wrapped.constraint_violations)

    bad_fields = json.dumps({"decision": "unknown", "amount_usd": 1200})
    res_bad = validate_structured_output(bad_fields, contract)
    assert res_bad.schema_valid is False
    assert "citations" in res_bad.missing_fields
    assert len(res_bad.constraint_violations) >= 2


def test_tool_call_sequence_f1_catches_reordering_and_arg_errors() -> None:
    expected = [
        ExpectedToolCall(name="verify_refund", required_args={"order_id": "ORD-88"}),
        ExpectedToolCall(name="issue_refund", required_args={"order_id": "ORD-88", "amount": 240}),
    ]
    exact = [
        PredictedToolCall(name="verify_refund", args={"order_id": "ORD-88"}),
        PredictedToolCall(name="issue_refund", args={"order_id": "ORD-88", "amount": 240}),
    ]
    res_exact = evaluate_tool_calls(expected, exact)
    assert res_exact.tool_f1 == pytest.approx(1.0, abs=1e-4)

    reversed_calls = [exact[1], exact[0]]
    res_rev = evaluate_tool_calls(expected, reversed_calls)
    assert res_rev.tool_f1 == pytest.approx(0.5, abs=1e-4)
    assert any("order mismatch" in v.lower() for v in res_rev.violations)


def test_vercel_env_uses_tmp_sqlite_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VERDICT_DB_PATH", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    assert resolve_db_path() == Path("/tmp/verdictops.db")


def test_cli_exit_codes_for_gate_pass_and_regression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_file = str(tmp_path / "cli_test.db")
    pass_code = cli.main(
        [
            "--db",
            db_file,
            "check",
            "--suite",
            "rag-grounding",
            "--candidate",
            "run-rg-candidate",
            "--baseline",
            "run-rg-baseline",
            "--min-faithfulness",
            "0.80",
            "--min-ndcg",
            "0.75",
            "--min-schema-pass",
            "0.95",
        ]
    )
    assert pass_code == 0

    fail_code = cli.main(
        [
            "--db",
            db_file,
            "check",
            "--suite",
            "rag-grounding",
            "--candidate",
            "run-rg-regression",
            "--baseline",
            "run-rg-baseline",
            "--min-faithfulness",
            "0.80",
            "--format",
            "json",
        ]
    )
    assert fail_code == 1
    captured = capsys.readouterr()
    parsed = json.loads(captured.out.strip().splitlines()[-1] if False else captured.out[captured.out.find("{"):])
    assert parsed["gate_verdict"] == "FAIL"
    assert len(parsed["violated_rules"]) >= 1

    live_fail = cli.main(
        [
            "--db",
            db_file,
            "run",
            "--suite",
            "hybrid-retrieval",
            "--pipeline",
            "prompt_unconstrained",
            "--format",
            "json",
        ]
    )
    assert live_fail == 1


def test_fastapi_endpoints_full_workflow(isolated_store: VerdictStore) -> None:
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    health_data = health.json()
    assert health_data["status"] == "ok"
    assert health_data["suite_count"] == 3
    assert health_data["total_cases"] == 36

    suites = client.get("/api/suites").json()
    assert len(suites) == 3
    assert all(s["case_count"] == 12 for s in suites)

    comp_pass = client.get(
        "/api/compare",
        params={
            "suite_id": "hybrid-retrieval",
            "baseline_id": "run-hr-baseline",
            "candidate_id": "run-hr-candidate",
        },
    )
    assert comp_pass.status_code == 200
    assert comp_pass.json()["gate_verdict"] == "PASS"

    comp_fail = client.get(
        "/api/compare",
        params={
            "suite_id": "tool-schema",
            "baseline_id": "run-ts-baseline",
            "candidate_id": "run-ts-regression",
        },
    )
    assert comp_fail.status_code == 200
    assert comp_fail.json()["gate_verdict"] == "FAIL"

    # Add custom golden test case and execute live sweep over all 13 cases
    new_case_resp = client.post(
        "/api/suites/rag-grounding/cases",
        json={
            "title": "Custom Snapshot Retention Rule",
            "query": "How long are encrypted DB snapshots kept before purge?",
            "category": "custom",
            "corpus_passages": [
                {
                    "doc_id": "DOC-CUST-1",
                    "title": "Snapshot Lifecycle",
                    "text": "Encrypted database snapshots are retained for 35 days before automated purge.",
                    "relevance": 2.0,
                }
            ],
            "relevant_docs": {"DOC-CUST-1": 2.0},
            "expected_claims": ["Encrypted database snapshots are retained for 35 days."],
            "forbidden_claims": ["Snapshots are deleted after 2 days."],
            "expected_tools": [],
            "schema_contract": {
                "name": "GroundedCitationResponse",
                "required_fields": ["answer", "citations", "confidence"],
                "fields": {
                    "answer": {"type": "string", "required": True, "min_length": 15},
                    "citations": {"type": "array", "required": True, "min_length": 1},
                    "confidence": {"type": "number", "required": True, "min_value": 0.0, "max_value": 1.0},
                },
            },
        },
    )
    assert new_case_resp.status_code == 201
    created_case = new_case_resp.json()
    assert created_case["case_code"] == "RG-13"

    exec_resp = client.post(
        "/api/runs/execute",
        json={
            "suite_id": "rag-grounding",
            "name": "Custom Sweep Check",
            "pipeline": "hybrid_rrf",
            "baseline_id": "run-rg-baseline",
            "bm25_weight": 0.35,
            "dense_weight": 0.65,
            "guardrail_strictness": 0.94,
            "schema_enforcement": True,
            "top_k": 5,
            "use_llm_judge": False,
        },
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["run"]["metrics"]["total_cases"] == 13
    assert exec_data["comparison"]["gate_verdict"] == "PASS"

    # Update gate policy to unattainable threshold and verify gate responds dynamically
    pol_resp = client.put(
        "/api/suites/rag-grounding/gate-policy",
        json={
            "min_ndcg": 0.99,
            "min_faithfulness": 0.99,
            "min_schema_pass": 0.99,
            "min_tool_f1": 0.90,
            "max_ndcg_drop": 0.01,
            "max_faithfulness_drop": 0.01,
            "max_p95_latency_ms": 500.0,
        },
    )
    assert pol_resp.status_code == 200
    recheck = client.get(
        "/api/compare",
        params={
            "suite_id": "rag-grounding",
            "baseline_id": "run-rg-baseline",
            "candidate_id": exec_data["run"]["id"],
        },
    ).json()
    assert recheck["gate_verdict"] == "FAIL"
