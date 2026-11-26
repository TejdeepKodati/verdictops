import React, { useState } from "react";
import { Check, Copy, Terminal } from "lucide-react";
import type { CompareResponse } from "../types";

interface ColophonProps {
  comparison: CompareResponse | null;
}

export const Colophon: React.FC<ColophonProps> = ({ comparison }) => {
  const [copied, setCopied] = useState(false);

  const suiteId = comparison?.suite.id ?? "rag-grounding";
  const candId = comparison?.candidate_run.id ?? "run-rg-candidate";
  const baseId = comparison?.baseline_run.id ?? "run-rg-baseline";
  const policy = comparison?.applied_policy;

  const cliCommand = `python -m backend.cli check --suite ${suiteId} --candidate ${candId} --baseline ${baseId} --min-faithfulness ${(
    policy?.min_faithfulness ?? 0.8
  ).toFixed(2)} --min-ndcg ${(policy?.min_ndcg ?? 0.75).toFixed(2)} --min-schema-pass ${(
    policy?.min_schema_pass ?? 0.9
  ).toFixed(2)}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cliCommand);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard API may be unavailable in restricted contexts
    }
  };

  return (
    <footer className="mt-10 border-t-2 border-ink pt-4 pb-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        {/* Left: CI Gate CLI Snippet */}
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">
            <Terminal className="h-3.5 w-3.5 text-burgundy" strokeWidth={1.75} aria-hidden="true" />
            <span>CI Regression Gate Command</span>
          </div>
          <div className="flex items-center gap-2 border border-rule bg-inset/70 px-3 py-2">
            <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-ink">
              {cliCommand}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy CI gate command"
              className="inline-flex shrink-0 items-center gap-1 border border-rule bg-surface px-2 py-1 text-[11px] font-medium text-ink transition-colors hover:bg-inset"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 text-forest" strokeWidth={2} aria-hidden="true" />
                  <span className="text-forest">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 text-muted" strokeWidth={1.75} aria-hidden="true" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right: Editorial Colophon Credit */}
        <div className="flex shrink-0 items-end justify-end md:pl-6">
          <a
            href="https://github.com/TejdeepKodati/verdictops"
            target="_blank"
            rel="noopener noreferrer"
            className="font-serif text-sm italic text-muted underline decoration-rule underline-offset-4 transition-colors hover:text-burgundy hover:decoration-burgundy"
          >
            {'made with \u2665 by Tejdeep'}
          </a>
        </div>
      </div>
    </footer>
  );
};
