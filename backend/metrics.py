"""Rigorous IR, Schema, Tool-Call, and Atomic Claim Faithfulness Evaluation Metrics."""

from __future__ import annotations

import json
import math
import re
from typing import Any

import httpx
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from backend.models import (
    AtomicClaimTrace,
    CorpusPassage,
    ExpectedToolCall,
    PredictedToolCall,
    SchemaContract,
    SchemaValidationResult,
    ToolEvaluationResult,
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "if", "in", "into", "is", "it", "its", "may", "might", "must",
    "of", "on", "or", "our", "out", "over", "shall", "should", "so", "such",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "to", "under", "up", "use", "used", "using", "was", "we", "were",
    "what", "when", "where", "which", "who", "will", "with", "would", "you",
    "your", "within", "via", "per", "each", "only", "also", "more", "than",
}

NEGATION_TOKENS = {
    "not", "no", "never", "neither", "nor", "cannot", "cant", "wont", "dont",
    "doesnt", "isnt", "arent", "prohibited", "forbidden", "disabled",
    "excluded", "ineligible", "unauthorized", "denied", "disallowed",
}

FILLER_PREFIXES = (
    "based on the provided context",
    "according to the documentation",
    "in summary",
    "here is the requested information",
    "note that",
)


def deduplicate_ranked(predicted_doc_ids: list[str]) -> list[str]:
    """Deduplicate ranked document IDs while preserving original rank order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for doc_id in predicted_doc_ids:
        if doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)
    return ordered


def precision_at_k(
    predicted_doc_ids: list[str],
    relevant_docs: dict[str, float],
    k: int = 5,
) -> float:
    """Compute Precision@K: fraction of top-K retrieved slots that are relevant."""
    if k <= 0:
        return 0.0
    ranked = deduplicate_ranked(predicted_doc_ids)[:k]
    if not ranked:
        return 0.0
    hits = sum(1 for doc_id in ranked if relevant_docs.get(doc_id, 0.0) > 0.0)
    return round(hits / float(k), 4)


def recall_at_k(
    predicted_doc_ids: list[str],
    relevant_docs: dict[str, float],
    k: int = 5,
) -> float:
    """Compute Recall@K: fraction of all relevant docs retrieved in top-K."""
    rel_set = {doc_id for doc_id, rel in relevant_docs.items() if rel > 0.0}
    if not rel_set:
        return 1.0
    if k <= 0:
        return 0.0
    ranked = deduplicate_ranked(predicted_doc_ids)[:k]
    hits = sum(1 for doc_id in ranked if doc_id in rel_set)
    return round(hits / float(len(rel_set)), 4)


def mrr(predicted_doc_ids: list[str], relevant_docs: dict[str, float]) -> float:
    """Compute Reciprocal Rank (1 / rank of first relevant document)."""
    ranked = deduplicate_ranked(predicted_doc_ids)
    for idx, doc_id in enumerate(ranked, start=1):
        if relevant_docs.get(doc_id, 0.0) > 0.0:
            return round(1.0 / float(idx), 4)
    return 0.0


def ndcg_at_k(
    predicted_doc_ids: list[str],
    relevant_docs: dict[str, float],
    k: int = 5,
) -> float:
    """Compute Normalized Discounted Cumulative Gain (NDCG@K) with graded relevance.

    Uses exponential gain: (2^rel - 1) / log2(rank + 1).
    """
    if k <= 0:
        return 0.0
    positive_rels = sorted((float(r) for r in relevant_docs.values() if r > 0.0), reverse=True)
    if not positive_rels:
        return 1.0

    ranked = deduplicate_ranked(predicted_doc_ids)[:k]
    if not ranked:
        return 0.0

    ranks = np.arange(1, len(ranked) + 1, dtype=np.float64)
    gains = np.array([max(0.0, float(relevant_docs.get(doc_id, 0.0))) for doc_id in ranked], dtype=np.float64)
    dcg = float(np.sum((np.power(2.0, gains) - 1.0) / np.log2(ranks + 1.0)))

    ideal_top_k = np.array(positive_rels[:k], dtype=np.float64)
    ideal_ranks = np.arange(1, len(ideal_top_k) + 1, dtype=np.float64)
    idcg = float(np.sum((np.power(2.0, ideal_top_k) - 1.0) / np.log2(ideal_ranks + 1.0)))
    if idcg <= 0.0:
        return 0.0
    return round(min(1.0, dcg / idcg), 4)


def compute_ir_metrics(
    predicted_doc_ids: list[str],
    relevant_docs: dict[str, float],
    k: int = 5,
) -> dict[str, float]:
    """Compute full suite of IR metrics at K."""
    return {
        "ndcg_at_5": ndcg_at_k(predicted_doc_ids, relevant_docs, k=k),
        "mrr": mrr(predicted_doc_ids, relevant_docs),
        "recall_at_5": recall_at_k(predicted_doc_ids, relevant_docs, k=k),
        "precision_at_5": precision_at_k(predicted_doc_ids, relevant_docs, k=k),
    }


def validate_structured_output(
    output_text: str,
    contract: SchemaContract | None,
) -> SchemaValidationResult:
    """Strictly validate candidate JSON output against a Pydantic v2 dynamic schema contract."""
    if contract is None:
        return SchemaValidationResult(applicable=False, schema_valid=True)

    stripped = output_text.strip()
    if stripped.startswith("```") or ("```json" in stripped and not stripped.startswith("{")):
        return SchemaValidationResult(
            applicable=True,
            schema_valid=False,
            missing_fields=list(contract.required_fields),
            constraint_violations=["Output wrapped in prose or markdown code fence instead of strict raw JSON"],
        )

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return SchemaValidationResult(
            applicable=True,
            schema_valid=False,
            missing_fields=list(contract.required_fields),
            constraint_violations=[f"Invalid JSON payload: {exc.msg} at char {exc.pos}"],
        )

    if not isinstance(parsed, dict):
        return SchemaValidationResult(
            applicable=True,
            schema_valid=False,
            missing_fields=list(contract.required_fields),
            constraint_violations=["Top-level JSON output must be a JSON object"],
        )

    # Build dynamic Pydantic v2 model from SchemaContract
    type_map: dict[str, Any] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list[Any],
        "object": dict[str, Any],
    }

    field_definitions: dict[str, tuple[Any, Any]] = {}
    all_field_names = set(contract.required_fields) | set(contract.fields.keys())
    for fname in all_field_names:
        spec = contract.fields.get(fname)
        is_req = fname in contract.required_fields or (spec.required if spec else False)
        py_type = type_map.get(spec.type, Any) if spec else Any

        field_kwargs: dict[str, Any] = {}
        if spec:
            if spec.min_value is not None and spec.type in ("integer", "number"):
                field_kwargs["ge"] = int(spec.min_value) if spec.type == "integer" else spec.min_value
            if spec.max_value is not None and spec.type in ("integer", "number"):
                field_kwargs["le"] = int(spec.max_value) if spec.type == "integer" else spec.max_value
            if spec.min_length is not None and spec.type in ("string", "array"):
                field_kwargs["min_length"] = spec.min_length
            if spec.pattern is not None and spec.type == "string":
                field_kwargs["pattern"] = spec.pattern

        if is_req:
            field_definitions[fname] = (py_type, Field(..., **field_kwargs))
        else:
            field_definitions[fname] = (py_type | None, Field(default=None, **field_kwargs))

    DynamicModel: type[BaseModel] = create_model(
        contract.name or "DynamicContract",
        __config__=ConfigDict(strict=False, extra="ignore"),
        **field_definitions,
    )

    missing_fields: list[str] = []
    violations: list[str] = []

    try:
        validated = DynamicModel.model_validate(parsed)
    except ValidationError as err:
        for error in err.errors():
            loc = ".".join(str(part) for part in error.get("loc", []))
            err_type = error.get("type", "")
            msg = error.get("msg", "Validation error")
            if err_type == "missing":
                missing_fields.append(loc)
                violations.append(f"Missing required field '{loc}'")
            else:
                violations.append(f"Field '{loc}': {msg}")
        validated = None

    # Additional strict type check: reject booleans posing as ints and check enum constraints
    for fname, spec in contract.fields.items():
        if fname in parsed and parsed[fname] is not None:
            val = parsed[fname]
            if spec.type == "integer" and isinstance(val, bool):
                violations.append(f"Field '{fname}' cannot be boolean when integer is expected")
            if spec.type == "number" and isinstance(val, bool):
                violations.append(f"Field '{fname}' cannot be boolean when number is expected")
            if spec.type == "string" and not isinstance(val, str):
                violations.append(f"Field '{fname}' must be a string, got {type(val).__name__}")
            if spec.enum is not None and val not in spec.enum:
                violations.append(f"Field '{fname}' value '{val}' not in allowed enum {spec.enum}")

    # Preserve deterministic order without duplicates
    missing_fields = list(dict.fromkeys(missing_fields))
    violations = list(dict.fromkeys(violations))

    return SchemaValidationResult(
        applicable=True,
        schema_valid=(validated is not None and len(violations) == 0),
        missing_fields=missing_fields,
        constraint_violations=violations,
    )


def _tool_args_match(
    expected_args: dict[str, Any],
    predicted_args: dict[str, Any],
    tool_name: str,
) -> tuple[bool, list[str]]:
    """Verify predicted tool call arguments satisfy expected required arguments."""
    errors: list[str] = []
    for key, exp_val in expected_args.items():
        if key not in predicted_args:
            errors.append(f"{tool_name}: missing required arg '{key}'")
            continue
        pred_val = predicted_args[key]
        if isinstance(exp_val, str) and isinstance(pred_val, str):
            if exp_val.strip().lower() != pred_val.strip().lower():
                errors.append(f"{tool_name}.{key}: expected '{exp_val}', got '{pred_val}'")
        elif isinstance(exp_val, (int, float)) and not isinstance(exp_val, bool):
            if isinstance(pred_val, bool) or not isinstance(pred_val, (int, float)):
                errors.append(f"{tool_name}.{key}: expected numeric {exp_val}, got {pred_val!r}")
            elif abs(float(exp_val) - float(pred_val)) > 1e-4:
                errors.append(f"{tool_name}.{key}: expected {exp_val}, got {pred_val}")
        elif pred_val != exp_val:
            errors.append(f"{tool_name}.{key}: expected {exp_val!r}, got {pred_val!r}")
    return (len(errors) == 0), errors


def evaluate_tool_calls(
    expected_tools: list[ExpectedToolCall],
    predicted_tools: list[PredictedToolCall],
) -> ToolEvaluationResult:
    """Evaluate tool-call precision, recall, and sequence F1 using ordered LCS matching."""
    if not expected_tools:
        return ToolEvaluationResult(applicable=False, tool_precision=1.0, tool_recall=1.0, tool_f1=1.0)

    if not predicted_tools:
        return ToolEvaluationResult(
            applicable=True,
            tool_precision=0.0,
            tool_recall=0.0,
            tool_f1=0.0,
            violations=[f"Expected {len(expected_tools)} tool call(s), got 0"],
        )

    n = len(expected_tools)
    m = len(predicted_tools)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    violations: list[str] = []

    # Check if two calls match (same tool name + valid required arguments)
    def calls_match(exp: ExpectedToolCall, pred: PredictedToolCall) -> bool:
        if exp.name != pred.name:
            return False
        ok, _ = _tool_args_match(exp.required_args, pred.args, exp.name)
        return ok

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if calls_match(expected_tools[i - 1], predicted_tools[j - 1]):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    lcs = dp[n][m]
    precision = lcs / float(m)
    recall = lcs / float(n)
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0.0 else 0.0

    # Diagnose specific mismatches for inspector trace
    if lcs < n or lcs < m:
        pred_names = [p.name for p in predicted_tools]
        exp_names = [e.name for e in expected_tools]
        if set(exp_names) == set(pred_names) and exp_names != pred_names:
            violations.append(f"Tool execution order mismatch: expected {exp_names}, got {pred_names}")
        for idx, exp in enumerate(expected_tools):
            matching_by_name = [p for p in predicted_tools if p.name == exp.name]
            if not matching_by_name:
                violations.append(f"Missing expected tool call '{exp.name}' (step {idx + 1})")
            else:
                # Report argument mismatch on best candidate call
                best_errs: list[str] | None = None
                matched_exact = False
                for p in matching_by_name:
                    ok, errs = _tool_args_match(exp.required_args, p.args, exp.name)
                    if ok:
                        matched_exact = True
                        break
                    if best_errs is None or len(errs) < len(best_errs):
                        best_errs = errs
                if not matched_exact and best_errs:
                    violations.extend(best_errs)
        unexpected = [p.name for p in predicted_tools if p.name not in exp_names]
        if unexpected:
            violations.append(f"Unexpected extra tool call(s): {unexpected}")

    violations = list(dict.fromkeys(violations))
    return ToolEvaluationResult(
        applicable=True,
        tool_precision=round(precision, 4),
        tool_recall=round(recall, 4),
        tool_f1=round(f1, 4),
        violations=violations,
    )


def _light_stem(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("es") and len(token) > 4 and token[-3] in ("s", "x", "z", "h"):
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    return token


def tokenize_content(text: str, stem: bool = True) -> list[str]:
    """Tokenize text into normalized content tokens (excluding stopwords)."""
    cleaned = re.sub(r"\[[A-Za-z0-9_-]+\]", " ", text)
    raw_tokens = re.findall(r"[a-z0-9]+(?:[./_-][a-z0-9]+)*", cleaned.lower())
    result: list[str] = []
    for tok in raw_tokens:
        if tok in STOPWORDS or len(tok) <= 1:
            continue
        result.append(_light_stem(tok) if stem else tok)
    return result


def extract_numbers(text: str) -> list[str]:
    """Extract normalized quantitative numbers, percentages, currencies, and ratios."""
    cleaned = re.sub(r"\[[A-Za-z0-9_-]+\]", " ", text)
    # Remove non-quantitative identifier codes like DOC-101, ORD-204, RFC-12, v2, SHA-256
    cleaned_no_ids = re.sub(r"\b[A-Za-z]{2,8}-\d+\b", " ", cleaned)
    matches = re.findall(r"(?<![a-zA-Z0-9_])[$€£]?\d+(?:,\d{3})*(?:\.\d+)?%?", cleaned_no_ids)
    normalized: list[str] = []
    for m in matches:
        core = m.lstrip("$€£").replace(",", "")
        is_pct = core.endswith("%")
        num_part = core[:-1] if is_pct else core
        try:
            val = float(num_part)
            # Represent integers cleanly (45.0 -> 45)
            norm_str = str(int(val)) if val.is_integer() else f"{val:g}"
        except ValueError:
            norm_str = num_part
        if is_pct:
            norm_str += "%"
        normalized.append(norm_str)
    return list(dict.fromkeys(normalized))


def extract_code_identifiers(text: str) -> list[str]:
    """Extract structured technical identifiers such as DOC-101, SLA-99, API codes."""
    cleaned = re.sub(r"\[[A-Za-z0-9_-]+\]", " ", text)
    ids = re.findall(r"\b[A-Z]{2,8}-\d+[A-Za-z0-9-]*\b", cleaned)
    return list(dict.fromkeys(ids))


def extract_readable_text_from_output(output_text: str) -> str:
    """Extract factual prose from plain text, raw JSON, or markdown-fenced JSON output."""
    stripped = output_text.strip()

    def _collect_json_prose(json_str: str) -> list[str]:
        data = json.loads(json_str)
        fragments: list[str] = []

        def collect(node: Any) -> None:
            if isinstance(node, str):
                if " " in node.strip() and len(node.strip()) >= 12:
                    fragments.append(node.strip())
            elif isinstance(node, list):
                for item in node:
                    collect(item)
            elif isinstance(node, dict):
                for k, v in node.items():
                    if k in ("citations", "doc_ids", "retrieved_docs", "tool_calls"):
                        continue
                    collect(v)

        collect(data)
        return fragments

    if stripped.startswith("{") or stripped.startswith("["):
        try:
            fragments = _collect_json_prose(stripped)
            if fragments:
                return " ".join(fragments)
        except json.JSONDecodeError:
            pass

    # Handle markdown-fenced or prose-wrapped JSON payloads without leaking JSON keys/confidence numbers
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, flags=re.DOTALL)
    if fence_match:
        try:
            fragments = _collect_json_prose(fence_match.group(1))
            if fragments:
                return " ".join(fragments)
        except json.JSONDecodeError:
            pass

    return stripped


def split_atomic_claims(text: str) -> list[str]:
    """Decompose an answer into atomic factual claim statements."""
    extracted = extract_readable_text_from_output(text)
    # Remove markdown formatting markers
    extracted = re.sub(r"```[a-zA-Z]*", "", extracted).replace("```", "")
    # Split on sentence boundaries and newlines
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", extracted)
    claims: list[str] = []

    for sent in raw_sentences:
        sent_clean = sent.strip(" -*\t\r\n")
        if not sent_clean:
            continue
        lower_s = sent_clean.lower()
        if any(lower_s.startswith(prefix) and len(sent_clean) < 60 for prefix in FILLER_PREFIXES):
            continue

        # Split compound clauses when each clause carries independent factual substance
        sub_clauses = re.split(r";\s+|,\s+(?:and|while|whereas|however)\s+", sent_clean)
        valid_sub = [c.strip(" .") for c in sub_clauses if len(tokenize_content(c)) >= 3]
        if len(valid_sub) >= 2:
            for clause in valid_sub:
                claims.append(clause + ".")
        elif len(tokenize_content(sent_clean)) >= 2:
            claims.append(sent_clean)

    return claims


def _bigrams(tokens: list[str]) -> list[tuple[str, str]]:
    if len(tokens) < 2:
        return []
    return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]


def _has_negation(text: str) -> bool:
    raw = re.findall(r"[a-z]+", text.lower())
    return any(tok in NEGATION_TOKENS for tok in raw)


def score_faithfulness(
    output_text: str,
    retrieved_contexts: list[CorpusPassage],
    forbidden_claims: list[str] | None = None,
) -> tuple[float, list[AtomicClaimTrace], list[str]]:
    """Score faithfulness of candidate output against retrieved context passages.

    Splits output into atomic claims, aligns each claim using normalized token overlap,
    IDF-weighted bigram similarity, numeric consistency checks, and negation polarity checks.
    Returns (faithfulness_score, claim_traces, forbidden_hits).
    """
    claims = split_atomic_claims(output_text)
    if not claims:
        # Output is pure structured enum/fields with no prose claims
        return 1.0, [], []

    if not retrieved_contexts:
        traces = [
            AtomicClaimTrace(
                claim=c,
                verdict="UNSUPPORTED",
                score=0.0,
                reason="No retrieved context passages available to verify claim",
            )
            for c in claims
        ]
        return 0.0, traces, []

    # Prepare passage sentences for granular alignment and IDF estimation
    passage_units: list[dict[str, Any]] = []
    all_context_numbers: set[str] = set()
    all_context_ids: set[str] = set()
    all_context_text_lower = " ".join(p.text.lower() for p in retrieved_contexts)

    for passage in retrieved_contexts:
        all_context_numbers.update(extract_numbers(passage.text))
        all_context_ids.update(extract_code_identifiers(passage.text))
        # Include full passage and individual sentences as alignment candidates
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", passage.text) if s.strip()]
        # Full passage unit
        p_tokens = tokenize_content(passage.text)
        passage_units.append({
            "doc_id": passage.doc_id,
            "text": passage.text,
            "tokens": set(p_tokens),
            "bigrams": set(_bigrams(p_tokens)),
            "has_neg": _has_negation(passage.text),
        })
        for s in sents:
            s_tokens = tokenize_content(s)
            if s_tokens:
                passage_units.append({
                    "doc_id": passage.doc_id,
                    "text": s,
                    "tokens": set(s_tokens),
                    "bigrams": set(_bigrams(s_tokens)),
                    "has_neg": _has_negation(s),
                })

    # Compute IDF weights over passage chunks (one doc per original passage)
    n_docs = max(1, len(retrieved_contexts))
    doc_freq: dict[str, int] = {}
    bigram_df: dict[tuple[str, str], int] = {}
    for passage in retrieved_contexts:
        toks = tokenize_content(passage.text)
        for t in set(toks):
            doc_freq[t] = doc_freq.get(t, 0) + 1
        for bg in set(_bigrams(toks)):
            bigram_df[bg] = bigram_df.get(bg, 0) + 1

    def token_idf(tok: str) -> float:
        return math.log((n_docs + 1.0) / (doc_freq.get(tok, 0) + 1.0)) + 1.0

    def bigram_idf(bg: tuple[str, str]) -> float:
        return math.log((n_docs + 1.0) / (bigram_df.get(bg, 0) + 1.0)) + 1.0

    traces: list[AtomicClaimTrace] = []
    for claim in claims:
        claim_toks = tokenize_content(claim)
        claim_tok_set = set(claim_toks)
        claim_bgs = _bigrams(claim_toks)
        claim_nums = extract_numbers(claim)
        claim_ids = extract_code_identifiers(claim)
        claim_neg = _has_negation(claim)

        # Find best matching passage unit
        best_unit: dict[str, Any] | None = None
        best_sim = -1.0
        best_tok_overlap = 0.0
        best_bg_sim = 0.0

        for unit in passage_units:
            if not claim_tok_set:
                continue
            matched_toks = claim_tok_set & unit["tokens"]
            tok_overlap = len(matched_toks) / float(len(claim_tok_set))

            if claim_bgs:
                total_bg_weight = sum(bigram_idf(bg) for bg in claim_bgs)
                matched_bg_weight = sum(bigram_idf(bg) for bg in claim_bgs if bg in unit["bigrams"])
                bg_sim = matched_bg_weight / total_bg_weight if total_bg_weight > 0 else 0.0
            else:
                total_tok_weight = sum(token_idf(t) for t in claim_tok_set)
                matched_tok_weight = sum(token_idf(t) for t in matched_toks)
                bg_sim = matched_tok_weight / total_tok_weight if total_tok_weight > 0 else 0.0

            # Also check IDF-weighted token recall as supportive signal when phrasing is paraphrased
            total_tok_weight = sum(token_idf(t) for t in claim_tok_set)
            matched_tok_weight = sum(token_idf(t) for t in matched_toks)
            idf_tok_recall = matched_tok_weight / total_tok_weight if total_tok_weight > 0 else tok_overlap

            combined_bg_or_idf = 0.65 * bg_sim + 0.35 * idf_tok_recall
            sim = 0.55 * tok_overlap + 0.45 * combined_bg_or_idf

            if sim > best_sim:
                best_sim = sim
                best_unit = unit
                best_tok_overlap = tok_overlap
                best_bg_sim = bg_sim

        # Check fabricated numbers not present in retrieved context
        fabricated_nums = [
            num for num in claim_nums
            if num not in all_context_numbers and num.rstrip("%") not in all_context_numbers
        ]
        fabricated_ids = [cid for cid in claim_ids if cid not in all_context_ids]
        numeric_mismatch = len(fabricated_nums) > 0

        # Check negation polarity contradiction against best matching sentence unit
        contradiction = False
        if best_unit is not None and best_tok_overlap >= 0.45:
            # Check sentence-level polarity flip when unit is a sentence
            if claim_neg != best_unit["has_neg"] and len(best_unit["text"]) < 320:
                contradiction = True

        reasons: list[str] = []
        if numeric_mismatch:
            verdict = "UNSUPPORTED"
            c_score = 0.0
            reasons.append(f"Fabricated numeric value(s) not in context: {fabricated_nums}")
        elif fabricated_ids:
            verdict = "UNSUPPORTED"
            c_score = 0.0
            reasons.append(f"Fabricated identifier(s) not in context: {fabricated_ids}")
        elif contradiction:
            verdict = "UNSUPPORTED"
            c_score = 0.0
            reasons.append("Polarity contradiction with aligned evidence passage")
        elif best_sim >= 0.50 or best_tok_overlap >= 0.70:
            verdict = "SUPPORTED"
            c_score = 1.0
            reasons.append(f"Aligned to {best_unit['doc_id']} (overlap={best_tok_overlap:.2f})")
        elif best_sim >= 0.28 or best_tok_overlap >= 0.42:
            verdict = "PARTIAL"
            c_score = 0.5
            reasons.append(f"Partial lexical alignment to {best_unit['doc_id']} (sim={best_sim:.2f})")
        else:
            verdict = "UNSUPPORTED"
            c_score = 0.0
            reasons.append("No sufficiently grounded evidence passage found")

        excerpt = best_unit["text"][:180] + ("..." if len(best_unit["text"]) > 180 else "") if best_unit else None
        traces.append(
            AtomicClaimTrace(
                claim=claim,
                verdict=verdict,
                score=c_score,
                matched_doc_id=best_unit["doc_id"] if best_unit else None,
                matched_passage_excerpt=excerpt,
                token_overlap=round(best_tok_overlap, 4),
                idf_bigram_similarity=round(best_bg_sim, 4),
                numeric_mismatch=numeric_mismatch,
                contradiction_detected=contradiction,
                reason="; ".join(reasons),
            )
        )

    # Check forbidden claims (explicit hallucination traps)
    forbidden_hits: list[str] = []
    output_lower = extract_readable_text_from_output(output_text).lower()
    if forbidden_claims:
        for fc in forbidden_claims:
            fc_clean = fc.strip().lower()
            if not fc_clean:
                continue
            # Match either direct substring or >=80% content token match + all numbers present
            fc_nums = extract_numbers(fc_clean)
            fc_toks = set(tokenize_content(fc_clean))
            out_toks = set(tokenize_content(output_lower))
            out_nums = set(extract_numbers(output_lower))
            if fc_clean in output_lower:
                forbidden_hits.append(fc)
            elif fc_toks and (len(fc_toks & out_toks) / len(fc_toks) >= 0.80) and all(n in out_nums for n in fc_nums):
                forbidden_hits.append(fc)

    base_score = sum(t.score for t in traces) / float(len(traces))
    if forbidden_hits:
        penalty = min(base_score, 0.25 * len(forbidden_hits))
        base_score = max(0.0, base_score - penalty)

    return round(base_score, 4), traces, forbidden_hits


def maybe_run_llm_judge(
    query: str,
    output_text: str,
    contexts: list[CorpusPassage],
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> tuple[str, float | None, str | None]:
    """Optional BYOK LLM-as-a-Judge evaluation; safely falls back to deterministic mode."""
    if not api_key or not api_key.strip():
        return "deterministic", None, None

    context_blob = "\n\n".join(f"[{p.doc_id}] {p.text}" for p in contexts[:5])
    prompt = (
        "You are a strict RAG faithfulness auditor. Given Context, Question, and Answer, "
        "return ONLY JSON: {\"score\": float in [0,1], \"rationale\": short string}.\n"
        f"Question: {query}\n\nContext:\n{context_blob}\n\nAnswer:\n{output_text}"
    )

    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            },
            timeout=8.0,
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            score = max(0.0, min(1.0, float(parsed.get("score", 0.0))))
            rationale = str(parsed.get("rationale", "LLM judge audit complete"))[:280]
            return "hybrid_llm_judge", round(score, 4), rationale
        return "deterministic_fallback", None, f"BYOK endpoint returned HTTP {resp.status_code}; deterministic scoring active"
    except Exception as exc:
        return "deterministic_fallback", None, f"BYOK judge skipped ({type(exc).__name__}); deterministic scoring active"
