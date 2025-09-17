import React from "react";

export function BulkImportPanel({ value, onChange, onSubmit }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow">
      <h3 className="text-lg font-semibold mb-2">Bulk Import (CSV)</h3>
      <p className="text-sm text-gray-600 mb-2">Paste rows (e.g., <code>bgg_id,title</code> …).</p>
      <textarea
        className="w-full h-40 border rounded-lg p-2 font-mono text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="mt-2">
        <button className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700" onClick={onSubmit}>
          Import
        </button>
      </div>
    </div>
  );
}

export function BulkCategorizePanel({ value, onChange, onSubmit }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow">
      <h3 className="text-lg font-semibold mb-2">Bulk Categorize Existing (CSV)</h3>
      <p className="text-sm text-gray-600 mb-2">
        Columns: <code>bgg_id,category[,title]</code>. Category accepts keys (e.g.,{" "}
        <code>CORE_STRATEGY</code>) or labels (e.g., <code>Core Strategy &amp; Epics</code>).
      </p>
      <textarea
        className="w-full h-40 border rounded-lg p-2 font-mono text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="mt-2">
        <button className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700" onClick={onSubmit}>
          Categorize
        </button>
      </div>
    </div>
  );
}
