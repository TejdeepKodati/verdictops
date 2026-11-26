"""Standalone CLI for running VerdictOps evaluation sweeps and CI regression gate checks.

Usage:
    python -m backend.cli check --suite rag-grounding --candidate run-rg-candidate --baseline run-rg-baseline
    python -m backend.cli run --suite rag-grounding --pipeline hybrid_rrf --min-faithfulness 0.80
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from backend.evaluator import compare_runs, execute_live_sweep
from backend.models import CompareResponse, ExecuteRunRequest
from backend.seed import seed_if_empty
from backend.store import VerdictStore


def _normalize_ratio(val: float | None) -> float | None:
    if val is None:
        return None
    return val / 100.0 if val > 1.0 else val


def _format_signed(val: float, decimals: int = 3, suffix: str = "") -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.{decimals}f}{suffix}"


def _print_table_report(comp: CompareResponse) -> None:
    bm = comp.baseline_run.metrics
    cm = comp.candidate_run.metrics
    dm = comp.deltas

    print("=" * 78)
    print(f"VERDICTOPS CI REGRESSION GATE REPORT :: {comp.suite.id} ({comp.suite.name})")
    print("=" * 78)
    print(f"Baseline : {comp.baseline_run.id} | {comp.baseline_run.name}")
    print(f"Candidate: {comp.candidate_run.id} | {comp.candidate_run.name}")
    print("-" * 78)
    print(f"{'Metric':<20} {'Baseline':>12} {'Candidate':>12} {'Delta':>14}")
    print("-" * 78)
    print(f"{'NDCG@5':<20} {bm.ndcg_at_5:>12.4f} {cm.ndcg_at_5:>12.4f} {_format_signed(dm.ndcg_at_5, 4):>14}")
    print(f"{'MRR':<20} {bm.mrr:>12.4f} {cm.mrr:>12.4f} {_format_signed(dm.mrr, 4):>14}")
    print(f"{'Recall@5':<20} {bm.recall_at_5:>12.4f} {cm.recall_at_5:>12.4f} {_format_signed(dm.recall_at_5, 4):>14}")
    print(f"{'Faithfulness':<20} {bm.faithfulness:>12.4f} {cm.faithfulness:>12.4f} {_format_signed(dm.faithfulness, 4):>14}")
    print(
        f"{'Schema Pass %':<20} "
        f"{bm.schema_pass_rate * 100:>11.1f}% "
        f"{cm.schema_pass_rate * 100:>11.1f}% "
        f"{_format_signed(dm.schema_pass_rate * 100, 1, '%'):>14}"
    )
    print(f"{'Tool Sequence F1':<20} {bm.tool_f1:>12.4f} {cm.tool_f1:>12.4f} {_format_signed(dm.tool_f1, 4):>14}")
    print(
        f"{'p95 Latency (ms)':<20} "
        f"{bm.p95_latency_ms:>12.1f} "
        f"{cm.p95_latency_ms:>12.1f} "
        f"{_format_signed(dm.p95_latency_ms, 1, ' ms'):>14}"
    )
    print("-" * 78)
    print(
        f"Cases: {comp.counts['all']} total | "
        f"{comp.counts['improved']} improved | "
        f"{comp.counts['regressions']} regressions | "
        f"{comp.counts['failed']} failed"
    )
    print(f"CI GATE VERDICT: {comp.gate_verdict}")
    if comp.violated_rules:
        print("Violated Rules:")
        for v in comp.violated_rules:
            print(f"  [FAIL] {v.rule}: {v.message} (expected {v.expected}, actual {v.actual})")
    print("=" * 78)


def _resolve_run_id(store: VerdictStore, suite_id: str, identifier: str | None, fallback_baseline: bool) -> str | None:
    runs = store.list_runs(suite_id)
    if not runs:
        return None
    if identifier is None:
        if fallback_baseline:
            base = next((r for r in runs if r.is_baseline), runs[0])
            return base.id
        return runs[-1].id
    for r in runs:
        if r.id == identifier or r.name.lower() == identifier.lower():
            return r.id
    return identifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.cli",
        description="VerdictOps CLI - Automated RAG & LLM Regression Gate Runner",
    )
    parser.add_argument("--db", default=None, help="Optional explicit SQLite database path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_gate_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--suite", required=True, help="Suite ID (rag-grounding, hybrid-retrieval, tool-schema)")
        p.add_argument("--baseline", default=None, help="Baseline run ID (defaults to suite baseline)")
        p.add_argument("--min-ndcg", type=float, default=None, help="Minimum required NDCG@5")
        p.add_argument("--min-faithfulness", type=float, default=None, help="Minimum required faithfulness score")
        p.add_argument("--min-schema-pass", type=float, default=None, help="Minimum schema pass ratio (0-1 or 0-100)")
        p.add_argument("--min-tool-f1", type=float, default=None, help="Minimum required tool sequence F1")
        p.add_argument("--max-ndcg-drop", type=float, default=None, help="Max allowed NDCG@5 drop vs baseline")
        p.add_argument("--format", choices=("table", "json"), default="table", help="Output format")

    check_p = subparsers.add_parser("check", help="Evaluate CI regression gate for an existing candidate run")
    add_gate_flags(check_p)
    check_p.add_argument("--candidate", required=True, help="Candidate run ID to check against gate")

    run_p = subparsers.add_parser("run", help="Execute a live evaluation sweep and evaluate CI regression gate")
    add_gate_flags(run_p)
    run_p.add_argument(
        "--pipeline",
        choices=("bm25_only", "hybrid_rrf", "prompt_guardrailed", "prompt_unconstrained", "custom_weights"),
        default="hybrid_rrf",
        help="Evaluation pipeline configuration",
    )
    run_p.add_argument("--name", default=None, help="Custom name for the evaluation run")
    run_p.add_argument("--bm25-weight", type=float, default=0.45, help="BM25 RRF weight for custom_weights")
    run_p.add_argument("--dense-weight", type=float, default=0.55, help="Dense RRF weight for custom_weights")
    run_p.add_argument("--guardrail-strictness", type=float, default=0.92, help="Guardrail strictness [0..1]")

    list_p = subparsers.add_parser("list-runs", help="List seeded and live evaluation runs for a suite")
    list_p.add_argument("--suite", required=True, help="Suite ID")
    list_p.add_argument("--format", choices=("table", "json"), default="table")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    store = VerdictStore(db_path=args.db)
    seed_if_empty(store)

    if args.command == "list-runs":
        runs = store.list_runs(args.suite)
        if args.format == "json":
            print(json.dumps([r.model_dump() for r in runs], indent=2))
        else:
            print(f"Runs for suite '{args.suite}':")
            for r in runs:
                tag = " [BASELINE]" if r.is_baseline else ""
                print(
                    f"  {r.id:<22} | {r.name:<46} | "
                    f"NDCG={r.metrics.ndcg_at_5:.3f} Faith={r.metrics.faithfulness:.3f} "
                    f"Schema={r.metrics.schema_pass_rate * 100:.1f}%{tag}"
                )
        return 0

    overrides = {
        k: v
        for k, v in {
            "min_ndcg": args.min_ndcg,
            "min_faithfulness": args.min_faithfulness,
            "min_schema_pass": _normalize_ratio(args.min_schema_pass),
            "min_tool_f1": args.min_tool_f1,
            "max_ndcg_drop": args.max_ndcg_drop,
        }.items()
        if v is not None
    }

    try:
        base_id = _resolve_run_id(store, args.suite, args.baseline, fallback_baseline=True)
        if args.command == "run":
            req = ExecuteRunRequest(
                suite_id=args.suite,
                name=args.name,
                pipeline=args.pipeline,
                baseline_id=base_id,
                bm25_weight=args.bm25_weight,
                dense_weight=args.dense_weight,
                guardrail_strictness=args.guardrail_strictness,
            )
            run, _ = execute_live_sweep(store, req)
            cand_id = run.id
        else:
            cand_id = _resolve_run_id(store, args.suite, args.candidate, fallback_baseline=False)

        comp = compare_runs(
            store=store,
            suite_id=args.suite,
            baseline_id=base_id,
            candidate_id=cand_id,
            policy_overrides=overrides or None,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(comp.model_dump(), indent=2))
    else:
        _print_table_report(comp)

    return 0 if comp.gate_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
