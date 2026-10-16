// src/components/staff/BackgroundTasksMenu.jsx
import React, { useState, useEffect, useRef } from "react";
import Icon from "../common/Icon";

/**
 * Header indicator for server-side background operations (imports, re-imports,
 * sleeve fetches). Those have no live progress API, so status is an estimate
 * based on elapsed time vs the expected duration.
 */
export function BackgroundTasksMenu({ operations = [], onDismiss }) {
  const [open, setOpen] = useState(false);
  const [, tick] = useState(0);
  const rootRef = useRef(null);

  useEffect(() => {
    if (operations.length === 0) return undefined;
    const t = setInterval(() => tick((n) => n + 1), 15000);
    return () => clearInterval(t);
  }, [operations.length]);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (operations.length === 0) return null;

  const now = Date.now();
  const running = operations.filter((op) => now - op.startedAt < op.etaMs).length;

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        className="inline-flex items-center gap-1.5 h-8 px-2.5 text-xs font-medium rounded-md border border-gray-300 bg-white hover:bg-gray-50"
      >
        <Icon name="tasks" size={14} className={running > 0 ? "text-blue-600" : "text-green-600"} />
        {running > 0 ? `${running} running` : "Tasks done"}
      </button>
      {open && (
        <div
          role="region"
          aria-label="Background tasks"
          className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 p-3 z-50"
        >
          <p className="text-xs text-gray-500 mb-2">Estimated status — these run on the server without live progress.</p>
          <ul className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
            {operations.map((op) => {
              const done = now - op.startedAt >= op.etaMs;
              return (
                <li key={op.id} className="py-2 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-sm text-gray-800 truncate">{op.label}</div>
                    <div className={`text-xs ${done ? "text-green-700" : "text-blue-600"}`}>
                      {done ? "Likely done" : "Running…"}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDismiss?.(op.id)}
                    aria-label={`Dismiss ${op.label}`}
                    className="p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
                  >
                    <Icon name="close" size={14} />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

export default BackgroundTasksMenu;
