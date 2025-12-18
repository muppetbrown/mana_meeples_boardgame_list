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

export function BulkAfterGamePanel({ value, onChange, onSubmit }) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow">
      <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
        🎲 Bulk Update AfterGame IDs (CSV)
      </h3>
      <p className="text-sm text-gray-600 mb-2">
        Columns: <code>bgg_id,aftergame_game_id[,title]</code>. AfterGame game ID should be a UUID (e.g.,{" "}
        <code>ac3a5f77-3e19-47af-a61a-d648d04b02e2</code>).
      </p>
      <div className="mb-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
        <p className="text-xs text-gray-700">
          <strong>Example CSV format:</strong><br />
          <code className="text-xs">
            bgg_id,aftergame_game_id,title<br />
            174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven<br />
            167791,bd4b6e88-4c2a-48bf-b71b-e759e15c13f3,Terraforming Mars
          </code>
        </p>
      </div>
      <textarea
        className="w-full h-40 border rounded-lg p-2 font-mono text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="bgg_id,aftergame_game_id,title&#10;174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven"
      />
      <div className="mt-2">
        <button className="px-4 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700" onClick={onSubmit}>
          Update AfterGame IDs
        </button>
      </div>
    </div>
  );
}
