// src/components/staff/ExpansionEditModal.jsx
import React, { useState, useEffect } from 'react';

/**
 * Modal for editing expansion details of a game
 * Allows manual configuration of expansion properties
 */
export default function ExpansionEditModal({ game, library, onSave, onClose }) {
  const [formData, setFormData] = useState({
    is_expansion: false,
    expansion_type: 'requires_base',
    base_game_id: null,
    modifies_players_min: null,
    modifies_players_max: null,
  });

  // Initialize form with game data
  useEffect(() => {
    if (game) {
      setFormData({
        is_expansion: game.is_expansion || false,
        expansion_type: game.expansion_type || 'requires_base',
        base_game_id: game.base_game_id || null,
        modifies_players_min: game.modifies_players_min || null,
        modifies_players_max: game.modifies_players_max || null,
      });
    }
  }, [game]);

  if (!game) return null;

  // Filter out the current game and expansions from base game selection
  const possibleBaseGames = library.filter(
    (g) => g.id !== game.id && !g.is_expansion
  );

  const handleChange = (field, value) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Prepare data - convert empty strings to null
    const saveData = {
      is_expansion: formData.is_expansion,
      expansion_type: formData.is_expansion ? formData.expansion_type : null,
      base_game_id: formData.is_expansion && formData.base_game_id ? parseInt(formData.base_game_id) : null,
      modifies_players_min: formData.modifies_players_min ? parseInt(formData.modifies_players_min) : null,
      modifies_players_max: formData.modifies_players_max ? parseInt(formData.modifies_players_max) : null,
    };

    onSave(saveData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6 rounded-t-2xl">
          <h2 className="text-2xl font-bold">Edit Expansion Details</h2>
          <p className="text-purple-100 mt-1 text-sm">{game.title}</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Is Expansion Toggle */}
          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
            <input
              type="checkbox"
              id="is_expansion"
              checked={formData.is_expansion}
              onChange={(e) => handleChange('is_expansion', e.target.checked)}
              className="w-5 h-5 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
            />
            <label htmlFor="is_expansion" className="font-semibold text-gray-900 cursor-pointer">
              This is an expansion
            </label>
          </div>

          {/* Expansion-specific fields (show only if is_expansion is true) */}
          {formData.is_expansion && (
            <div className="space-y-4 border-l-4 border-purple-300 pl-4">
              {/* Expansion Type */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Expansion Type
                </label>
                <select
                  value={formData.expansion_type}
                  onChange={(e) => handleChange('expansion_type', e.target.value)}
                  className="w-full border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
                >
                  <option value="requires_base">Requires Base Game</option>
                  <option value="standalone">Standalone (can be played alone)</option>
                  <option value="both">Both (standalone OR with base game)</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  {formData.expansion_type === 'requires_base' && '🔒 Will NOT appear in public catalogue'}
                  {formData.expansion_type === 'standalone' && '✅ Will appear in public catalogue'}
                  {formData.expansion_type === 'both' && '✅ Will appear in public catalogue'}
                </p>
              </div>

              {/* Base Game Selection */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Base Game (Optional)
                </label>
                <select
                  value={formData.base_game_id || ''}
                  onChange={(e) => handleChange('base_game_id', e.target.value ? e.target.value : null)}
                  className="w-full border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
                >
                  <option value="">-- None --</option>
                  {possibleBaseGames.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.title} {g.year ? `(${g.year})` : ''}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Link this expansion to its base game for better organization
                </p>
              </div>

              {/* Player Count Modifications */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Modified Player Count (Optional)
                </label>
                <div className="flex gap-3 items-center">
                  <div className="flex-1">
                    <input
                      type="number"
                      min="1"
                      max="99"
                      value={formData.modifies_players_min || ''}
                      onChange={(e) => handleChange('modifies_players_min', e.target.value)}
                      placeholder="Min"
                      className="w-full border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
                    />
                  </div>
                  <span className="text-gray-500 font-medium">to</span>
                  <div className="flex-1">
                    <input
                      type="number"
                      min="1"
                      max="99"
                      value={formData.modifies_players_max || ''}
                      onChange={(e) => handleChange('modifies_players_max', e.target.value)}
                      placeholder="Max"
                      className="w-full border-2 border-gray-300 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 rounded-lg px-4 py-2 outline-none transition-all"
                    />
                  </div>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  If this expansion extends the player count (e.g., "5-6 Player Extension")
                </p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 rounded-lg border-2 border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-medium hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
