import React from "react";
import BulkResultSummary from "./BulkResultSummary";

/** Read a chosen .csv/.txt file into the textarea. */
function CsvFileButton({ onText, disabled }) {
  return (
    <label className={`inline-flex items-center px-3 py-2 rounded border border-gray-300 text-sm cursor-pointer hover:bg-gray-50 ${disabled ? "opacity-50 pointer-events-none" : ""}`}>
      Load from file…
      <input
        type="file"
        accept=".csv,.txt,text/csv,text/plain"
        className="sr-only"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          onText(await file.text());
          e.target.value = "";
        }}
      />
    </label>
  );
}

function lineCount(text) {
  return (text || "").split("\n").filter((l) => l.trim()).length;
}

function BulkPanelShell({ title, children, value, onChange, onSubmit, busy, submitLabel, buttonClass, placeholder, result, resultLogName, onDismissResult, note }) {
  const lines = lineCount(value);
  return (
    <div className="bg-white rounded-2xl p-6 shadow">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      {children}
      <textarea
        className="w-full h-40 border rounded-lg p-2 font-mono text-sm"
        aria-label={title}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        disabled={busy}
      />
      <div className="mt-2 flex items-center gap-3 flex-wrap">
        <button
          className={`px-4 py-2 rounded text-white disabled:opacity-50 disabled:cursor-not-allowed ${buttonClass}`}
          onClick={onSubmit}
          disabled={busy || lines === 0}
        >
          {busy ? "Working…" : lines > 0 ? `${submitLabel} (${lines} line${lines === 1 ? "" : "s"})` : submitLabel}
        </button>
        <CsvFileButton onText={onChange} disabled={busy} />
        {value && !busy && (
          <button type="button" className="text-sm text-gray-600 underline" onClick={() => onChange("")}>
            Clear
          </button>
        )}
      </div>
      {note}
      {result && (
        <BulkResultSummary result={result} logName={resultLogName} onDismiss={onDismissResult} />
      )}
    </div>
  );
}

export function BulkImportPanel({ value, onChange, onSubmit, busy = false, queued, onDismissQueued }) {
  return (
    <BulkPanelShell
      title="Bulk Import (CSV)"
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
      busy={busy}
      submitLabel="Import"
      buttonClass="bg-green-600 hover:bg-green-700"
      placeholder={"30549\n174430,Gloomhaven"}
      note={
        queued && (
          <div className="mt-3 p-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800 flex justify-between gap-3" role="status">
            <span>
              {queued.message} New games will appear in Manage Library as they finish — refresh it in a minute or two.
            </span>
            {onDismissQueued && (
              <button onClick={onDismissQueued} aria-label="Dismiss" className="text-green-800">✕</button>
            )}
          </div>
        )
      }
    >
      <p className="text-sm text-gray-600 mb-2">Paste rows (e.g., <code>bgg_id,title</code> …). Imports run in the background.</p>
    </BulkPanelShell>
  );
}

export function BulkCategorizePanel({ value, onChange, onSubmit, busy = false, result, onDismissResult }) {
  return (
    <BulkPanelShell
      title="Bulk Categorize Existing (CSV)"
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
      busy={busy}
      submitLabel="Categorize"
      buttonClass="bg-blue-600 hover:bg-blue-700"
      placeholder={"30549,GATEWAY_STRATEGY\n174430,Core Strategy & Epics"}
      result={result}
      resultLogName="categorize"
      onDismissResult={onDismissResult}
    >
      <p className="text-sm text-gray-600 mb-2">
        Columns: <code>bgg_id,category[,title]</code>. Category accepts keys (e.g.,{" "}
        <code>CORE_STRATEGY</code>) or labels (e.g., <code>Core Strategy &amp; Epics</code>).
      </p>
    </BulkPanelShell>
  );
}

export function BulkAfterGamePanel({ value, onChange, onSubmit, busy = false, result, onDismissResult }) {
  return (
    <BulkPanelShell
      title="🎲 Bulk Update AfterGame IDs (CSV)"
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
      busy={busy}
      submitLabel="Update AfterGame IDs"
      buttonClass="bg-emerald-600 hover:bg-emerald-700"
      placeholder={"bgg_id,aftergame_game_id,title\n174430,ac3a5f77-3e19-47af-a61a-d648d04b02e2,Gloomhaven"}
      result={result}
      resultLogName="aftergame-ids"
      onDismissResult={onDismissResult}
    >
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
    </BulkPanelShell>
  );
}
