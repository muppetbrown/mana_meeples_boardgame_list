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

      {/* System Maintenance Section */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-2">System Maintenance</h2>
        <p className="text-sm text-gray-600 mb-4">
          Critical operations for database integrity and data management
        </p>

        <div className="space-y-4">
          {/* Re-import All Games */}
          <div className="p-4 rounded-lg border-2 border-red-200 bg-red-50">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-red-900">Re-import All Games</h3>
                <p className="text-sm text-red-800 mt-1">
                  Fetches latest BoardGameGeek data for all games in the library. This operation
                  can take <strong>several minutes</strong> depending on library size and BGG API
                  response times.
                </p>
              </div>
            </div>
            <div className="mt-3 p-3 bg-white rounded border border-red-200">
              <div className="text-xs text-gray-600 space-y-1">
                <div><strong>Use when:</strong> BGG data needs refreshing (ratings, complexity, images)</div>
                <div><strong>Duration:</strong> ~2-5 minutes for 100 games</div>
                <div><strong>Safe:</strong> Yes - existing manual data is preserved</div>
              </div>
            </div>
          </div>

          {/* Fix Database Sequence */}
          <div className="p-4 rounded-lg border-2 border-yellow-200 bg-yellow-50">
            <div>
              <h3 className="font-semibold text-yellow-900">Fix Database Sequence</h3>
              <p className="text-sm text-yellow-800 mt-1">
                Resets the PostgreSQL ID sequence to prevent "duplicate key" errors when adding
                new games. This is a safe operation that resolves sequence conflicts.
              </p>
            </div>
            <div className="mt-3 p-3 bg-white rounded border border-yellow-200">
              <div className="text-xs text-gray-600 space-y-1">
                <div><strong>Use when:</strong> Getting "duplicate primary key" errors on game creation</div>
                <div><strong>Duration:</strong> Instant</div>
                <div><strong>Safe:</strong> Yes - only resets ID counter</div>
              </div>
            </div>
          </div>

          {/* Export Games CSV */}
          <div className="p-4 rounded-lg border-2 border-teal-200 bg-teal-50">
            <div>
              <h3 className="font-semibold text-teal-900">Export Games CSV</h3>
              <p className="text-sm text-teal-800 mt-1">
                Downloads complete game database as CSV file with timestamped filename. Useful for
                backups, analysis, or migration.
              </p>
            </div>
            <div className="mt-3 p-3 bg-white rounded border border-teal-200">
              <div className="text-xs text-gray-600 space-y-1">
                <div><strong>Use when:</strong> Creating backups or analyzing data externally</div>
                <div><strong>Duration:</strong> Instant</div>
                <div><strong>Safe:</strong> Yes - read-only operation</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Debug & Monitoring Section */}
      <div className="bg-white rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-2">Debug & Monitoring</h2>
        <p className="text-sm text-gray-600 mb-4">
          System health checks and performance diagnostics
        </p>

        <div className="grid md:grid-cols-2 gap-4 mb-4">
          <div className="p-4 rounded-lg border border-blue-200 bg-blue-50">
            <h3 className="font-semibold text-blue-900 mb-2">System Health</h3>
            <p className="text-sm text-blue-800">
              Check API and database connectivity status, verify system is operational
            </p>
          </div>

          <div className="p-4 rounded-lg border border-blue-200 bg-blue-50">
            <h3 className="font-semibold text-blue-900 mb-2">Performance Stats</h3>
            <p className="text-sm text-blue-800">
              View request timing, slow query tracking, and performance metrics
            </p>
          </div>

          <div className="p-4 rounded-lg border border-blue-200 bg-blue-50">
            <h3 className="font-semibold text-blue-900 mb-2">Database Info</h3>
            <p className="text-sm text-blue-800">
              Inspect database structure, view sample data, check table schemas
            </p>
          </div>

          <div className="p-4 rounded-lg border border-blue-200 bg-blue-50">
            <h3 className="font-semibold text-blue-900 mb-2">BGG Categories</h3>
            <p className="text-sm text-blue-800">
              View all unique BoardGameGeek categories present in the database
            </p>
          </div>
        </div>

        <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-xs text-gray-600">
            <strong>💡 Tip:</strong> All debug data can be downloaded as JSON files for detailed analysis or sharing with developers.
          </div>
        </div>
      </div>

      {/* Admin Tools Panel */}
      <AdminToolsPanel onToast={showToast} onLibraryReload={loadLibrary} />

      {/* Help & Documentation */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-2xl p-6 border border-gray-200">
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
