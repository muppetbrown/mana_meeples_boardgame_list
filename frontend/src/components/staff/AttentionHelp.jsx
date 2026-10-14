// src/components/staff/AttentionHelp.jsx
import React from "react";
import { ATTENTION_FILTERS } from "../../utils/libraryQuality";

/**
 * "How to fix this" guidance shown in Manage Library while a
 * needs-attention filter is active.
 */
export function AttentionHelp({ filterKey, count, onClear }) {
  const filter = ATTENTION_FILTERS.find((f) => f.key === filterKey);
  if (!filter) return null;

  return (
    <section
      className="mt-4 p-4 rounded-lg border border-orange-200 bg-orange-50"
      aria-label={`How to fix: ${filter.label}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-orange-900">
            {filter.label}
            {typeof count === "number" && ` · ${count} game${count === 1 ? "" : "s"}`}
          </h3>
          <p className="text-sm text-orange-800 mt-1">{filter.fix.why}</p>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="shrink-0 text-sm px-3 py-1.5 rounded-lg border border-orange-300 bg-white text-orange-900 hover:bg-orange-100"
        >
          Clear filter
        </button>
      </div>
      <p className="text-sm font-medium text-orange-900 mt-3">How to fix this</p>
      <ol className="list-decimal list-inside space-y-1 mt-1 text-sm text-gray-800">
        {filter.fix.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </section>
  );
}

export default AttentionHelp;
