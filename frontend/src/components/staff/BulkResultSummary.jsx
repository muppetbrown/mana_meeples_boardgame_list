// src/components/staff/BulkResultSummary.jsx
import React from "react";

/** Build a plain-text log from a { updated, not_found, errors } bulk result. */
export function buildBulkLog(result) {
  return [
    "Updated:",
    ...(result.updated || []),
    "",
    "Not found:",
    ...(result.not_found || []),
    "",
    "Errors:",
    ...(result.errors || []),
    "",
  ].join("\n");
}

export function downloadTextFile(name, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Section({ title, items, tone, defaultOpen }) {
  if (!items || items.length === 0) return null;
  return (
    <details open={defaultOpen} className={`rounded-lg border ${tone} p-3`}>
      <summary className="cursor-pointer text-sm font-semibold">
        {title} ({items.length})
      </summary>
      <ul className="mt-2 max-h-48 overflow-y-auto text-xs font-mono space-y-0.5">
        {items.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
    </details>
  );
}

/**
 * Inline per-row results for bulk CSV operations, with a log download.
 * result = { updated: string[], not_found: string[], errors: string[] }
 */
export function BulkResultSummary({ result, logName = "bulk-result", onDismiss }) {
  if (!result) return null;
  const hasProblems = (result.not_found?.length || 0) + (result.errors?.length || 0) > 0;
  return (
    <div className="mt-4 space-y-2" role="status" aria-label="Bulk operation results">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-gray-800">
          Last run: {result.updated?.length || 0} updated · {result.not_found?.length || 0} not found ·{" "}
          {result.errors?.length || 0} errors
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
            onClick={() => {
              const ts = new Date().toISOString().replace(/[:.]/g, "-");
              downloadTextFile(`${logName}-${ts}.log.txt`, buildBulkLog(result));
            }}
          >
            Download log
          </button>
          {onDismiss && (
            <button type="button" className="text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200" onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      </div>
      <Section title="Errors" items={result.errors} tone="border-red-200 bg-red-50 text-red-800" defaultOpen />
      <Section title="Not found" items={result.not_found} tone="border-amber-200 bg-amber-50 text-amber-800" defaultOpen={!hasProblems ? false : true} />
      <Section title="Updated" items={result.updated} tone="border-green-200 bg-green-50 text-green-800" defaultOpen={!hasProblems} />
    </div>
  );
}

export default BulkResultSummary;
