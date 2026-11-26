import React, { useEffect, useState } from "react";
import { Plus, Sparkles, X } from "lucide-react";
import type { EvalCaseCreate } from "../types";

interface AddCaseModalProps {
  open: boolean;
  suiteId: string;
  suiteName: string;
  onClose: () => void;
  onCreateCase: (payload: EvalCaseCreate, rerunAfterSave: boolean) => Promise<void>;
}

export const AddCaseModal: React.FC<AddCaseModalProps> = ({
  open,
  suiteId,
  suiteName,
  onClose,
  onCreateCase,
}) => {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("custom");
  const [query, setQuery] = useState("");
  const [primaryDocId, setPrimaryDocId] = useState("DOC-CUSTOM-01");
  const [primaryDocTitle, setPrimaryDocTitle] = useState("Canonical Policy Specification");
  const [primaryDocText, setPrimaryDocText] = useState("");
  const [distractorText, setDistractorText] = useState("");
  const [expectedClaimsText, setExpectedClaimsText] = useState("");
  const [forbiddenClaimsText, setForbiddenClaimsText] = useState("");
  const [includeSchema, setIncludeSchema] = useState(true);
  const [toolName, setToolName] = useState("");
  const [toolArgsJson, setToolArgsJson] = useState("{}");
  const [rerunAfterSave, setRerunAfterSave] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const handleLoadSample = () => {
    setTitle("Webhook Signature Replay Window Enforcement");
    setCategory("security");
    setQuery("How old can an incoming webhook timestamp be before signature verification rejects it?");
    setPrimaryDocId("DOC-CUSTOM-SEC-01");
    setPrimaryDocTitle("Webhook Timestamp Tolerance Standard");
    setPrimaryDocText(
      "Webhook receivers enforce a strict 300-second replay window on the X-Verdict-Timestamp header and reject older requests with HTTP 401.",
    );
    setDistractorText(
      "Webhook exponential retry queues retain failed outbound deliveries for up to 72 hours.",
    );
    setExpectedClaimsText("Webhook receivers reject timestamps older than 300 seconds with HTTP 401.");
    setForbiddenClaimsText("Webhook receivers accept stale signatures up to 24 hours old.");
    if (suiteId === "tool-schema") {
      setToolName("verify_webhook_signature");
      setToolArgsJson('{"max_age_seconds": 300}');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (title.trim().length < 3 || query.trim().length < 5 || primaryDocText.trim().length < 10) {
      setError("Please provide a title, query, and primary ground-truth context passage.");
      return;
    }

    let parsedToolArgs: Record<string, unknown> = {};
    if (toolName.trim()) {
      try {
        parsedToolArgs = JSON.parse(toolArgsJson || "{}");
      } catch {
        setError("Expected Tool Arguments must be valid JSON.");
        return;
      }
    }

    const passages = [
      {
        doc_id: primaryDocId.trim() || "DOC-CUSTOM-01",
        title: primaryDocTitle.trim() || "Primary Evidence",
        text: primaryDocText.trim(),
        relevance: 2.0,
      },
    ];
    if (distractorText.trim()) {
      passages.push({
        doc_id: "DOC-CUSTOM-DIST",
        title: "Related Non-Answer Note",
        text: distractorText.trim(),
        relevance: 0.0,
      });
    }

    const payload: EvalCaseCreate = {
      title: title.trim(),
      category: category.trim() || "custom",
      query: query.trim(),
      corpus_passages: passages,
      relevant_docs: { [passages[0].doc_id]: 2.0 },
      expected_claims: expectedClaimsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      forbidden_claims: forbiddenClaimsText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      expected_tools: toolName.trim()
        ? [{ name: toolName.trim(), required_args: parsedToolArgs }]
        : [],
      schema_contract: includeSchema
        ? {
            name: "CustomCitationContract",
            required_fields: ["answer", "citations", "confidence"],
            fields: {
              answer: { type: "string", required: true, min_length: 15 },
              citations: { type: "array", required: true, min_length: 1 },
              confidence: {
                type: "number",
                required: true,
                min_value: 0.0,
                max_value: 1.0,
              },
            },
          }
        : null,
    };

    setSubmitting(true);
    try {
      await onCreateCase(payload, rerunAfterSave);
      setTitle("");
      setQuery("");
      setPrimaryDocText("");
      setDistractorText("");
      setExpectedClaimsText("");
      setForbiddenClaimsText("");
      setToolName("");
      setToolArgsJson("{}");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save golden test case");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-case-title"
    >
      <div className="max-h-[92vh] w-full max-w-2xl overflow-y-auto border border-rule bg-surface shadow-2xl">
        <div className="flex items-center justify-between border-b border-rule bg-inset/70 px-5 py-3.5">
          <div>
            <h2 id="add-case-title" className="font-serif text-base font-bold text-ink">
              Add Golden Test Case
            </h2>
            <p className="font-mono text-[11px] text-muted">Target Suite: {suiteName}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleLoadSample}
              className="inline-flex items-center gap-1 border border-rule bg-surface px-2.5 py-1 text-[11px] font-medium text-ink hover:bg-inset"
            >
              <Sparkles className="h-3 w-3 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
              <span>Fill Example</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close add test case modal"
              className="inline-flex h-8 w-8 items-center justify-center border border-rule bg-surface text-ink hover:bg-inset"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5 text-xs">
          {error && (
            <div role="alert" className="border border-crimson/40 bg-[#FEF2F2] p-3 text-crimson">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <label htmlFor="case-title" className="mb-1 block font-semibold text-ink">
                Case Title
              </label>
              <input
                id="case-title"
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Webhook Replay Window Enforcement"
                className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
              />
            </div>
            <div>
              <label htmlFor="case-category" className="mb-1 block font-semibold text-ink">
                Category
              </label>
              <input
                id="case-category"
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="security"
                className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
              />
            </div>
          </div>

          <div>
            <label htmlFor="case-query" className="mb-1 block font-semibold text-ink">
              Evaluation Query / Prompt
            </label>
            <textarea
              id="case-query"
              required
              rows={2}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask the exact question or agent task to evaluate..."
              className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
            />
          </div>

          <div className="space-y-3 border border-rule bg-inset/50 p-3.5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label htmlFor="primary-doc-id" className="mb-1 block font-semibold text-ink">
                  Ground-Truth Doc ID
                </label>
                <input
                  id="primary-doc-id"
                  type="text"
                  value={primaryDocId}
                  onChange={(e) => setPrimaryDocId(e.target.value)}
                  className="w-full border border-rule bg-surface px-2.5 py-1.5 font-mono text-xs text-ink"
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="primary-doc-title" className="mb-1 block font-semibold text-ink">
                  Document Title
                </label>
                <input
                  id="primary-doc-title"
                  type="text"
                  value={primaryDocTitle}
                  onChange={(e) => setPrimaryDocTitle(e.target.value)}
                  className="w-full border border-rule bg-surface px-2.5 py-1.5 text-xs text-ink"
                />
              </div>
            </div>

            <div>
              <label htmlFor="primary-doc-text" className="mb-1 block font-semibold text-ink">
                Authoritative Passage Text (rel=2.0)
              </label>
              <textarea
                id="primary-doc-text"
                required
                rows={2}
                value={primaryDocText}
                onChange={(e) => setPrimaryDocText(e.target.value)}
                placeholder="Paste the exact authoritative text passage that answers the query..."
                className="w-full border border-rule bg-surface px-3 py-2 text-xs text-ink"
              />
            </div>

            <div>
              <label htmlFor="distractor-doc-text" className="mb-1 block font-medium text-muted">
                Optional Lexical Distractor Passage (rel=0.0)
              </label>
              <input
                id="distractor-doc-text"
                type="text"
                value={distractorText}
                onChange={(e) => setDistractorText(e.target.value)}
                placeholder="Optional distractor passage sharing keywords without answering the query..."
                className="w-full border border-rule bg-surface px-3 py-1.5 text-xs text-ink"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="expected-claims" className="mb-1 block font-semibold text-ink">
                Expected Claims (1 per line)
              </label>
              <textarea
                id="expected-claims"
                rows={2}
                value={expectedClaimsText}
                onChange={(e) => setExpectedClaimsText(e.target.value)}
                placeholder="Key factual statements required..."
                className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
              />
            </div>
            <div>
              <label htmlFor="forbidden-claims" className="mb-1 block font-semibold text-ink">
                Forbidden Hallucinations (1 per line)
              </label>
              <textarea
                id="forbidden-claims"
                rows={2}
                value={forbiddenClaimsText}
                onChange={(e) => setForbiddenClaimsText(e.target.value)}
                placeholder="Hallucination traps that must not appear..."
                className="w-full border border-rule bg-canvas px-3 py-2 text-xs text-ink"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="expected-tool-name" className="mb-1 block font-medium text-muted">
                Optional Expected Tool Name
              </label>
              <input
                id="expected-tool-name"
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                placeholder="e.g., verify_webhook_signature"
                className="w-full border border-rule bg-canvas px-3 py-1.5 font-mono text-xs text-ink"
              />
            </div>
            <div>
              <label htmlFor="expected-tool-args" className="mb-1 block font-medium text-muted">
                Required Tool Arguments (JSON)
              </label>
              <input
                id="expected-tool-args"
                type="text"
                value={toolArgsJson}
                onChange={(e) => setToolArgsJson(e.target.value)}
                placeholder='{"max_age_seconds": 300}'
                className="w-full border border-rule bg-canvas px-3 py-1.5 font-mono text-xs text-ink"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2 border-t border-rule pt-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-ink">
                <input
                  type="checkbox"
                  checked={includeSchema}
                  onChange={(e) => setIncludeSchema(e.target.checked)}
                  className="accent-[#9F1239]"
                />
                <span>Attach Grounded Citation JSON Schema contract</span>
              </label>
              <label className="flex items-center gap-2 font-medium text-ink">
                <input
                  type="checkbox"
                  checked={rerunAfterSave}
                  onChange={(e) => setRerunAfterSave(e.target.checked)}
                  className="accent-[#9F1239]"
                />
                <span>Execute live Hybrid RRF sweep immediately after saving</span>
              </label>
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="border border-rule bg-surface px-4 py-2 font-semibold text-muted hover:text-ink"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-1.5 bg-burgundy px-4 py-2 font-semibold text-white hover:bg-[#881337] disabled:opacity-60"
              >
                <Plus className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
                <span>{submitting ? "Saving..." : "Save Golden Case"}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
