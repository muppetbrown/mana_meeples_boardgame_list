// src/components/staff/tabs/AdvancedToolsTab.jsx
import React from "react";
import { useStaff } from "../../../context/StaffContext";
import { AdminToolsPanel } from "../AdminToolsPanel";

/**
 * Advanced Tools tab - System maintenance, debugging, and data export
 */
export function AdvancedToolsTab() {
  const { showToast, loadLibrary } = useStaff();

  return (
    <div className="space-y-6">
      {/* Warning Banner */}
      <div className="bg-yellow-50 rounded-2xl p-5 border-2 border-yellow-200">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="text-lg font-semibold text-yellow-900 mb-2">
              Advanced System Tools
            </h3>
            <p className="text-sm text-yellow-800">
              These tools are designed for system maintenance and troubleshooting. Some operations
              may take several minutes to complete and affect all games in the database.{" "}
              <strong>Use with caution.</strong>
            </p>
          </div>
        </div>
      </div>

      {/* Admin Tools Panel */}
      <AdminToolsPanel onToast={showToast} onLibraryReload={loadLibrary} />

      {/* Help & Documentation */}
      <div className="bg-linear-to-r from-gray-50 to-gray-100 rounded-2xl p-6 border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">📖 Need Help?</h3>
        <div className="space-y-2 text-sm text-gray-700">
          <div className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Performance issues?</strong> Check Performance Stats to identify slow queries
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Database errors?</strong> Try Fix Database Sequence first, then check System Health
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Outdated game data?</strong> Use Re-import All Games to refresh from BoardGameGeek
            </span>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-purple-600 font-bold">•</span>
            <span>
              <strong>Regular backups:</strong> Export Games CSV monthly to maintain data backups
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
