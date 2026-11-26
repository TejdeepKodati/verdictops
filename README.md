# VerdictOps — Automated RAG & LLM Output Quality Evaluation Harness

VerdictOps is a production-grade evaluation harness and CI regression gate for RAG retrieval pipelines, atomic claim faithfulness verification, and structured tool-calling contracts.

Built with **Python 3.12 + FastAPI + Pydantic v2 + NumPy + SQLite** on the backend, a standalone **CI Gate CLI**, and a **React + TypeScript + Vite + Tailwind CSS** editorial diff workbench on the frontend.

---

## Architecture Overview

```
verdictops/
├── api/index.py               # FastAPI serverless entrypoint (Vercel & uvicorn compatible)
├── backend/
│   ├── models.py              # Pydantic v2 models for suites, golden cases, runs, gates & traces
│   ├── metrics.py             # Graded IR metrics, Pydantic v2 schema validator, LCS tool F1, atomic claim scorer
│   ├── store.py               # SQLite store (./data/verdictops.db locally, /tmp/verdictops.db on Vercel)
│   ├── seed.py                # 3 golden suites x 12 test cases (36 cases) + 9 pre-evaluated runs
│   ├── evaluator.py           # Hybrid BM25 + dense concept RRF retriever, live sweep runner & comparator
│   └── cli.py                 # Standalone CI Regression Gate CLI (exit code 0 on PASS, 1 on FAIL)
├── sql/postgres_schema.sql    # Production PostgreSQL schema matching the SQLite layout
├── src/                       # Editorial Benchmark Broadsheet UI (React + TypeScript + Tailwind)
├── tests/test_verdictops.py   # Pytest suite verifying IR math, hallucinations, schemas, CLI & FastAPI
├── Dockerfile & docker-compose.yml
└── vercel.json
```

---

## Evaluation Suites & Golden Datasets

VerdictOps ships with **36 curated golden test cases** across 3 specialized evaluation suites (12 cases per suite), each pre-evaluated with 3 runs (`Baseline`, `Passing Candidate`, and `Regression Candidate`):

1. **`rag-grounding` — RAG Grounding & Citation Fidelity**
   - Enterprise compliance, SLA schedules, security rotation, and DR policy cases (`RG-01` .. `RG-12`).
   - Tests evidence grounding, numeric consistency, forbidden hallucination traps, and citation JSON contracts.
2. **`hybrid-retrieval` — Hybrid Search & Ranking Quality**
   - Distributed systems, database pooling, vector index, and ML infra queries (`HR-01` .. `HR-12`) with graded relevance (`rel=2.0` primary, `rel=1.0` supporting, `rel=0.0` lexical-trap distractors).
   - Demonstrates why Okapi BM25 alone falls for keyword overlap while Hybrid RRF bridges semantic concepts (`tail latency` <-> `p99 mitigation`, `hot partition` <-> `key skew`).
3. **`tool-schema` — Tool-Calling & Structured Output Contracts**
   - FinOps, SRE incident escalation, IAM rotation, and GDPR erasure agent workflows (`TS-01` .. `TS-12`).
   - Validates ordered multi-step tool calls, argument accuracy, and strict raw JSON Pydantic v2 contracts.

---

## Mathematical Metric Definitions

### 1. Information Retrieval Metrics (`backend/metrics.py`)
Ranked document predictions are deduplicated while preserving rank order:

- **Precision@K**:
  $$\text{Precision@K} = \frac{|\{\text{doc} \in \text{top}_K : \text{rel}(\text{doc}) > 0\}|}{K}$$
- **Recall@K**:
  $$\text{Recall@K} = \frac{|\{\text{doc} \in \text{top}_K : \text{rel}(\text{doc}) > 0\}|}{|\{\text{doc} \in \mathcal{D}_{\text{rel}} : \text{rel}(\text{doc}) > 0\}|}$$
- **Mean Reciprocal Rank (MRR)**:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$
  where $\text{rank}_q$ is the 1-based position of the first relevant document ($0$ if none retrieved).
- **Graded NDCG@K** (computed with `numpy`):
  $$\text{DCG@K} = \sum_{i=1}^{\min(K, |\text{pred}|)} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}, \qquad \text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$

### 2. Atomic Claim Faithfulness (`score_faithfulness`)
1. Decomposes prose (or factual fields inside JSON responses) into **atomic claims**.
2. Aligns every claim against sentence and passage units in retrieved contexts using:
   - Normalized content token overlap (with stopword filtering and suffix normalization),
   - **IDF-weighted bigram similarity**,
   - **Numeric & code-identifier consistency verification** (catching fabricated SLA percentages, dollar figures, and day counts),
   - **Negation polarity contradiction checks**.
3. Assigns `SUPPORTED` (`1.0`), `PARTIAL` (`0.5`), or `UNSUPPORTED` (`0.0`) per claim, flags triggered `forbidden_claims`, and optionally pairs with a BYOK LLM-as-a-Judge (`X-LLM-Api-Key` header).

### 3. Structured Output & Tool-Call Sequence Metrics
- **Pydantic v2 Dynamic Contract Validator (`validate_structured_output`)**: Rejects prose/markdown wrappers, constructs a dynamic `pydantic.BaseModel` via `create_model`, and reports `schema_valid`, `missing_fields`, and `constraint_violations` (types, enums, numeric bounds, regex patterns).
- **Ordered Tool Sequence F1 (`evaluate_tool_calls`)**: Computes Longest Common Subsequence (LCS) alignment between expected and predicted `(tool_name, validated_required_args)` sequences to produce `tool_precision`, `tool_recall`, and `tool_f1`.

---

## Standalone CI Regression Gate CLI

Run checks directly in CI/CD pipelines (returns exit code `0` on `PASS`, exit code `1` on `FAIL`):

```bash
# Check an existing candidate run against baseline & threshold gates
python -m backend.cli check \
  --suite rag-grounding \
  --candidate run-rg-candidate \
  --baseline run-rg-baseline \
  --min-faithfulness 0.80 \
  --min-ndcg 0.75 \
  --min-schema-pass 0.95

# Catch an unconstrained prompt regression (exits with code 1)
python -m backend.cli check \
  --suite rag-grounding \
  --candidate run-rg-regression \
  --baseline run-rg-baseline

# Execute a live evaluation sweep and output JSON gate verdict
python -m backend.cli run \
  --suite hybrid-retrieval \
  --pipeline hybrid_rrf \
  --format json
```

---

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm

### 1. Start the Backend API
```bash
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```

### 2. Start the Frontend UI
```bash
npm install
npm run dev
```
Open `http://127.0.0.1:5173`. Vite proxies `/api/*` directly to `http://127.0.0.1:8000`.

### 3. Run Tests
```bash
pytest -v
npm run build
```

---

## Docker & Vercel Deployment

### Docker Compose
```bash
docker compose up --build
```
Serves both the built UI and FastAPI backend on `http://localhost:8000` with persistent SQLite storage mounted at `/app/data`.

### Vercel Serverless
`vercel.json` builds the Vite SPA to `dist/` and routes `/api/*` to `api/index.py`. When `VERCEL` is detected (or the working directory is read-only), VerdictOps automatically places SQLite at `/tmp/verdictops.db` and seeds on cold start so live sweeps and custom test cases work without readonly errors. For multi-instance production persistence, apply `sql/postgres_schema.sql` to PostgreSQL.
