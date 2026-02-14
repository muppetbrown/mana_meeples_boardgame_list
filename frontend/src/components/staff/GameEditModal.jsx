// src/components/staff/GameEditModal.jsx
import React, { useState, useEffect } from 'react';
import { CATEGORY_KEYS, CATEGORY_LABELS } from '../../constants/categories';
import SleevesListTable from './SleevesListTable';

/**
 * Unified modal for editing all game properties:
 * - Category assignment
 * - Expansion details
 * - Sleeve status
 */
export default function GameEditModal({ game, library, onSave, onClose }) {
  const [activeTab, setActiveTab] = useState('category');
  const [formData, setFormData] = useState({
    // Category
    mana_meeple_category: null,
    // Expansion
    is_expansion: false,
    expansion_type: 'requires_base',
    base_game_id: null,
    modifies_players_min: null,
    modifies_players_max: null,
    // AfterGame integration
    aftergame_game_id: null,
  });

  // Initialize form with game data
  useEffect(() => {
    if (game) {
      setFormData({
        mana_meeple_category: game.mana_meeple_category || null,
        is_expansion: game.is_expansion || false,
        expansion_type: game.expansion_type || 'requires_base',
        base_game_id: game.base_game_id || null,
        modifies_players_min: game.modifies_players_min || null,
        modifies_players_max: game.modifies_players_max || null,
        aftergame_game_id: game.aftergame_game_id || null,
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

  // UUID validation pattern
  const isValidUUID = (str) => {
    if (!str) return true; // Empty is valid (optional field)
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidPattern.test(str);
  };

  const [validationErrors, setValidationErrors] = React.useState([]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const errors = [];

    // Validate player counts if provided
    const minPlayers = formData.modifies_players_min ? parseInt(formData.modifies_players_min) : null;
    const maxPlayers = formData.modifies_players_max ? parseInt(formData.modifies_players_max) : null;

    if (minPlayers !== null && (minPlayers < 1 || minPlayers > 99)) {
      errors.push("Min players must be between 1 and 99");
    }
    if (maxPlayers !== null && (maxPlayers < 1 || maxPlayers > 99)) {
      errors.push("Max players must be between 1 and 99");
    }
    if (minPlayers !== null && maxPlayers !== null && minPlayers > maxPlayers) {
      errors.push("Min players cannot be greater than max players");
    }

    // Validate AfterGame UUID format
    if (formData.aftergame_game_id && !isValidUUID(formData.aftergame_game_id)) {
      errors.push("AfterGame ID must be a valid UUID format (e.g., ac3a5f77-3e19-47af-a61a-d648d04b02e2)");
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    setValidationErrors([]);

    // Prepare data - convert empty strings to null
    const saveData = {
      mana_meeple_category: formData.mana_meeple_category || null,
      is_expansion: formData.is_expansion,
      expansion_type: formData.is_expansion ? formData.expansion_type : null,
      base_game_id: formData.is_expansion && formData.base_game_id ? parseInt(formData.base_game_id) : null,
      modifies_players_min: formData.modifies_players_min ? parseInt(formData.modifies_players_min) : null,
      modifies_players_max: formData.modifies_players_max ? parseInt(formData.modifies_players_max) : null,
      aftergame_game_id: formData.aftergame_game_id || null,
    };

    onSave(saveData);
  };

  const tabs = [
    { id: 'category', label: '📑 Category', icon: '📑' },
    { id: 'expansion', label: '🎯 Expansion', icon: '🎯' },
    { id: 'sleeves', label: '🃏 Sleeves', icon: '🃏' },
    { id: 'integration', label: '🎲 AfterGame', icon: '🎲' },
  ];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-linear-to-r from-purple-600 to-indigo-600 text-white p-6 rounded-t-2xl">
          <h2 className="text-2xl font-bold">Edit Game</h2>
          <p className="text-purple-100 mt-1 text-sm">{game.title}</p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 bg-gray-50">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 px-6 py-4 text-sm font-semibold transition-all ${
                  activeTab === tab.id
                    ? 'bg-white text-purple-600 border-b-2 border-purple-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Category Tab */}
          {activeTab === 'category' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-3">
                  Assign Category
                </label>
                <div className="grid grid-cols-1 gap-3">
                  {CATEGORY_KEYS.map((key) => (
                    <label
                      key={key}
                      className={`flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        formData.mana_meeple_category === key
                          ? 'border-purple-500 bg-purple-50 shadow-md'
                          : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="category"
                        value={key}
                        checked={formData.mana_meeple_category === key}
                        onChange={(e) => handleChange('mana_meeple_category', e.target.value)}
                        className="w-5 h-5 text-purple-600"
                      />
                      <span className="font-medium text-gray-900">
                        {CATEGORY_LABELS[key]}
                      </span>
                    </label>
                  ))}
                  <label
                    className={`flex items-center gap-3 p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      formData.mana_meeple_category === null
                        ? 'border-gray-500 bg-gray-50 shadow-md'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="category"
                      value=""
                      checked={formData.mana_meeple_category === null}
                      onChange={() => handleChange('mana_meeple_category', null)}
                      className="w-5 h-5 text-gray-600"
                    />
                    <span className="font-medium text-gray-700">
                      Uncategorized
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Expansion Tab */}
          {activeTab === 'expansion' && (
            <div className="space-y-6">
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

              {/* Expansion-specific fields */}
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
            </div>
          )}

          {/* Sleeves Tab */}
          {activeTab === 'sleeves' && (
            <div className="space-y-4">
              <SleevesListTable
                gameId={game.id}
                onSleeveUpdate={() => {
                  // Optionally refresh parent data
                }}
              />

              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-sm text-gray-700">
                  <strong>Note:</strong> Mark individual sleeve types as sleeved above.
                  The shopping list will only include unmarked sleeve types.
                </p>
              </div>
            </div>
          )}

          {/* AfterGame Integration Tab */}
          {activeTab === 'integration' && (
            <div className="space-y-4">
              <div className="p-4 bg-linear-to-r from-emerald-50 to-teal-50 rounded-lg border border-emerald-200">
                <p className="text-sm text-gray-700 mb-2">
                  <strong>🎲 AfterGame Integration</strong>
                </p>
                <p className="text-xs text-gray-600">
                  Connect this game to AfterGame to enable players to plan game sessions directly from the library.
                  Enter the AfterGame game ID (UUID format) to enable deep linking.
                </p>
              </div>

              <div>
                <label htmlFor="aftergame_game_id" className="block text-sm font-semibold text-gray-700 mb-2">
                  AfterGame Game ID
                </label>
                <input
                  type="text"
                  id="aftergame_game_id"
                  value={formData.aftergame_game_id || ''}
                  onChange={(e) => handleChange('aftergame_game_id', e.target.value.trim() || null)}
                  placeholder="e.g., ac3a5f77-3e19-47af-a61a-d648d04b02e2"
                  className="w-full border-2 border-gray-300 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 rounded-lg px-4 py-2 outline-none transition-all font-mono text-sm"
                />
                <p className="mt-2 text-xs text-gray-500">
                  Find the game ID in AfterGame's URL or database. Format: UUID (36 characters with dashes)
                </p>
              </div>

              {formData.aftergame_game_id && (
                <div className="p-3 bg-green-50 rounded-lg border border-green-200">
                  <p className="text-sm text-green-800">
                    ✅ When set, the "Plan a Game" button will link directly to this specific game on AfterGame
                  </p>
                </div>
              )}

              {!formData.aftergame_game_id && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-800">
                    ℹ️ Without an AfterGame ID, the "Plan a Game" button will link to the generic game creation page
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-sm font-semibold text-red-800 mb-2">Please fix the following errors:</p>
              <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-6 mt-6 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 rounded-lg border-2 border-gray-300 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-lg bg-linear-to-r from-purple-600 to-indigo-600 text-white font-medium hover:from-purple-700 hover:to-indigo-700 transition-all shadow-lg hover:shadow-xl"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
