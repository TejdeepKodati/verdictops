# DESIGN.md - VerdictOps

## Visual Concept
Editorial Benchmark Broadsheet: a scholarly warm-paper and plum-ink evaluation notebook modeled after statistical lab reports and regression diff sheets. Uses clean horizontal ledger rules and an expandable tabular diff matrix instead of rounded KPI dashboard cards.

## Color Palette
- `--bg-canvas`: `#FAF7F2` (Warm Bone Paper ground)
- `--bg-surface`: `#FFFFFF` (Clean Sheet diff table and detail rows)
- `--bg-inset`: `#F1ECE3` (Warm Sand comparison inset)
- `--text-primary`: `#1B1424` (Deep Plum Ink primary text)
- `--text-muted`: `#5E5468` (Warm Taupe metadata and headers)
- `--border`: `#DDD5C7` (Warm Rule 1px dividers)
- `--primary`: `#9F1239` (Imperial Burgundy primary CTAs and regression flags)
- `--success`: `#047857` (Forest Green passing gate and metric improvements)
- `--warning`: `#B45309` (Ochre latency and soft-warning markers)
- `--danger`: `#B91C1C` (Crimson CI regression gate failures)

## Typography
- Section and Suite Headings: `Bitter` (slab-serif authority for benchmark reports and case headers)
- Body, Controls, and Table Cells: `Public Sans` (clean, legible tabular UI font)
- Exact Decimals, Deltas, and Assertions: `JetBrains Mono` (monospace alignment for `NDCG@5`, `MRR`, `Recall@5`, faithfulness scores, and latency)

## Layout and Navigation Model
- Left `260px` **Suite & Experiment Sidebar**: choose evaluation suite, select Baseline Run vs Candidate Run for side-by-side comparison, launch a live evaluation sweep, or submit a new golden test case. Collapses into a clean slide-over drawer/bar on mobile (`<900px`).
- Main analytical sheet:
  - Top **Horizontal Ledger Summary Strip** separated by vertical hairlines and anchored by a bottom rule (explicitly avoiding identical KPI boxes): displays CI Gate Verdict (`PASS` / `FAIL`), `NDCG@5`, `Faithfulness`, `Schema Pass %`, and `p95 Latency` with signed deltas relative to the selected baseline.
  - Filterable **Per-Case Regression Diff Matrix** (`All`, `Regressions`, `Failed`, `Improved`) where selecting any row expands an inline diff inspector comparing Baseline vs Candidate output, retrieved document IDs, atomic claim faithfulness verdicts, and schema assertion traces.
- Editorial bottom colophon row with the CI gate command snippet on the left and the credit link `made with \u2665 by Tejdeep` (rendered with heart glyph) in taupe/burgundy serif on the **bottom right** linking directly to `https://github.com/TejdeepKodati/verdictops`.

## Why It Fits
LLM evaluation engineers audit prompt and retrieval regressions by reading exact metric deltas and comparing baseline versus candidate outputs per test case; a scholarly ledger and inline diff matrix maximizes clarity and eliminates decorative card noise.

## Accessibility and Responsiveness Principles
- High-contrast ink-on-paper readability (`>=4.5:1`), horizontal-scroll-safe table wrappers (`overflow-x-auto`) with stacked summary cards on narrow mobile viewports (`375px`), clear `2px solid #9F1239` keyboard focus outlines, `prefers-reduced-motion` support, and zero horizontal overflow or hidden elements.
