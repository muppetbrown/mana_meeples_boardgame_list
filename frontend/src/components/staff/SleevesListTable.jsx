import React, { useState, useEffect } from 'react';
import { getGameSleeves, updateSleeveStatus, createGameSleeve, deleteGameSleeve, updateGameSleeveStatus } from '../../api/client';

const EMPTY_FORM = { card_name: '', width_mm: '', height_mm: '', quantity: '', notes: '' };

const STATUS_INFO = {
  found: { icon: '🃏', label: 'Sleeve data found (from BGG)' },
  none: { icon: '🚫🃏', label: 'No sleeves needed' },
  manual: { icon: '🃏', label: 'Sleeve data added manually' },
  error: { icon: '❓🃏', label: 'Scraper error - needs investigation' },
  not_found: { icon: '❓🃏', label: 'Not found on BGG - needs investigation' },
  check: { icon: '❓🃏', label: 'Needs investigation' },
};

export default function SleevesListTable({ gameId, hasSleeves, onSleeveUpdate }) {
  const [sleeves, setSleeves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [stockFeedback, setStockFeedback] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState(EMPTY_FORM);
  const [addError, setAddError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [gameSleeveStatus, setGameSleeveStatus] = useState(hasSleeves || null);
  const [statusUpdating, setStatusUpdating] = useState(false);

  useEffect(() => {
    setGameSleeveStatus(hasSleeves || null);
  }, [hasSleeves, gameId]);

  useEffect(() => {
    loadSleeves();
  }, [gameId]);

  const handleSetGameStatus = async (status) => {
    setStatusUpdating(true);
    try {
      const result = await updateGameSleeveStatus(gameId, status);
      setGameSleeveStatus(result.has_sleeves);
      await loadSleeves();
      if (onSleeveUpdate) {
        onSleeveUpdate();
      }
    } catch (error) {
      console.error('Failed to update game sleeve status:', error);
    } finally {
      setStatusUpdating(false);
    }
  };

  const loadSleeves = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await getGameSleeves(gameId);
      setSleeves(data);
    } catch (error) {
      console.error('Failed to load sleeves:', error);
      setLoadError(
        error?.response?.status
          ? `Failed to load sleeve data (HTTP ${error.response.status}). Please retry.`
          : 'Failed to load sleeve data. Check your connection and retry.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSleeve = async (sleeveId, currentStatus) => {
    try {
      const result = await updateSleeveStatus(sleeveId, !currentStatus);
      // Show stock deduction feedback
      if (result.stock_info) {
        const info = result.stock_info;
        const msg = info.warning
          ? `${info.warning}`
          : `${info.product_name}: stock now ${info.new_stock}`;
        setStockFeedback(msg);
        setTimeout(() => setStockFeedback(null), 3000);
      }
      await loadSleeves();
      if (onSleeveUpdate) {
        onSleeveUpdate();
      }
    } catch (error) {
      console.error('Failed to update sleeve status:', error);
    }
  };

  const handleDeleteSleeve = async (sleeveId) => {
    if (!window.confirm('Remove this sleeve requirement?')) return;
    try {
      await deleteGameSleeve(sleeveId);
      await loadSleeves();
      if (onSleeveUpdate) {
        onSleeveUpdate();
      }
    } catch (error) {
      console.error('Failed to delete sleeve:', error);
    }
  };

  const handleAddSleeve = async (e) => {
    // This lives inside GameEditModal's own outer <form>, so it must never be
    // a nested <form>/submit itself (invalid HTML - the browser will fall
    // back to a full-page submit/reload, discarding whatever was typed).
    // Called from a plain button's onClick; e is defensive in case that changes.
    e?.preventDefault?.();
    setAddError(null);

    const width_mm = parseInt(addForm.width_mm, 10);
    const height_mm = parseInt(addForm.height_mm, 10);
    const quantity = parseInt(addForm.quantity, 10);

    if (!Number.isFinite(width_mm) || !Number.isFinite(height_mm) || !Number.isFinite(quantity)) {
      setAddError('Width, height, and quantity must be numbers.');
      return;
    }

    setSaving(true);
    try {
      await createGameSleeve(gameId, {
        card_name: addForm.card_name.trim() || null,
        width_mm,
        height_mm,
        quantity,
        notes: addForm.notes.trim() || null,
      });
      // Backend marks the game "manual" when a sleeve is added by hand.
      setGameSleeveStatus('manual');
      setAddForm(EMPTY_FORM);
      setShowAddForm(false);
      await loadSleeves();
      if (onSleeveUpdate) {
        onSleeveUpdate();
      }
    } catch (error) {
      console.error('Failed to add sleeve:', error);
      setAddError('Failed to add sleeve requirement. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const fullySleeved = sleeves.length > 0 && sleeves.every(s => s.is_sleeved);
  const sleevedCount = sleeves.filter(s => s.is_sleeved).length;

  if (loading) {
    return <div className="text-center py-4">Loading sleeve requirements...</div>;
  }

  const statusInfo = STATUS_INFO[gameSleeveStatus] || { icon: '❓🃏', label: 'Needs investigation (never checked)' };
  const statusHeader = (
    <div className="p-3 bg-gray-50 rounded-lg border flex items-center justify-between gap-3 flex-wrap">
      <span className="text-sm text-gray-700">
        <span className="mr-1">{statusInfo.icon}</span>
        <strong>Status:</strong> {statusInfo.label}
      </span>
      <div className="flex gap-2">
        {gameSleeveStatus !== 'none' && (
          <button
            type="button"
            onClick={() => handleSetGameStatus('none')}
            disabled={statusUpdating}
            title="Mark this game as having no cards to sleeve"
            className="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-700 text-white disabled:bg-gray-400"
          >
            Mark No Sleeves Needed
          </button>
        )}
        {gameSleeveStatus && (
          <button
            type="button"
            onClick={() => handleSetGameStatus('check')}
            disabled={statusUpdating}
            title="Reset to needs-investigation"
            className="px-2 py-1 text-xs rounded bg-gray-200 hover:bg-gray-300 text-gray-700 disabled:opacity-50"
          >
            Reset Status
          </button>
        )}
      </div>
    </div>
  );

  const addFormPanel = (
    <div className="border rounded-lg p-4 bg-gray-50">
      {!showAddForm ? (
        <button
          type="button"
          onClick={() => setShowAddForm(true)}
          className="px-3 py-1.5 text-sm rounded-lg bg-green-600 hover:bg-green-700 text-white"
        >
          + Add Sleeve Requirement
        </button>
      ) : (
        // Deliberately a <div>, not a <form>: this renders inside
        // GameEditModal's own outer <form>, and nested <form> elements are
        // invalid HTML - the browser falls back to a full-page submit
        // instead of running React's handler, which reloads the page and
        // discards whatever was typed. All buttons below use type="button"
        // and call handlers directly instead of relying on form submission.
        <div className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Card type (optional)"
              value={addForm.card_name}
              onChange={(e) => setAddForm({ ...addForm, card_name: e.target.value })}
              className="col-span-2 px-2 py-1.5 border rounded text-sm"
            />
            <input
              type="number"
              placeholder="Width (mm)"
              value={addForm.width_mm}
              onChange={(e) => setAddForm({ ...addForm, width_mm: e.target.value })}
              className="px-2 py-1.5 border rounded text-sm"
            />
            <input
              type="number"
              placeholder="Height (mm)"
              value={addForm.height_mm}
              onChange={(e) => setAddForm({ ...addForm, height_mm: e.target.value })}
              className="px-2 py-1.5 border rounded text-sm"
            />
            <input
              type="number"
              placeholder="Quantity"
              value={addForm.quantity}
              onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })}
              className="px-2 py-1.5 border rounded text-sm"
            />
            <input
              type="text"
              placeholder="Notes (optional)"
              value={addForm.notes}
              onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })}
              className="col-span-3 px-2 py-1.5 border rounded text-sm"
            />
          </div>
          {addError && <p className="text-sm text-red-600">{addError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleAddSleeve}
              disabled={saving}
              className="px-3 py-1.5 text-sm rounded-lg bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-400"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => { setShowAddForm(false); setAddForm(EMPTY_FORM); setAddError(null); }}
              className="px-3 py-1.5 text-sm rounded-lg bg-gray-200 hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );

  if (loadError) {
    return (
      <div className="space-y-4">
        {statusHeader}
        <div className="p-4 bg-red-50 rounded-lg border border-red-200 flex items-center justify-between gap-4">
          <p className="text-sm text-red-700">{loadError}</p>
          <button
            type="button"
            onClick={loadSleeves}
            className="px-3 py-1.5 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white whitespace-nowrap"
          >
            Retry
          </button>
        </div>
        {addFormPanel}
      </div>
    );
  }

  if (sleeves.length === 0) {
    return (
      <div className="space-y-4">
        {statusHeader}
        <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
          <p className="text-sm text-gray-700">
            No sleeve requirements defined for this game.
            {gameSleeveStatus === 'none' && ' (Marked as not needing sleeves.)'}
          </p>
        </div>
        {addFormPanel}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {statusHeader}
      {/* Fully Sleeved Indicator */}
      {fullySleeved && (
        <div className="p-3 bg-green-50 rounded-lg border border-green-300 flex items-center gap-2">
          <span className="text-2xl">🃏</span>
          <span className="font-semibold text-green-800">
            All sleeve requirements are marked as sleeved!
          </span>
        </div>
      )}

      {/* Stock feedback */}
      {stockFeedback && (
        <div className="p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
          {stockFeedback}
        </div>
      )}

      {/* Sleeves Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">
                Sleeved
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">
                Card Type
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">
                Size (mm)
              </th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-700 uppercase">
                Quantity
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">
                Matched Product
              </th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">
                Notes
              </th>
              <th className="px-4 py-2 text-right text-xs font-semibold text-gray-700 uppercase">
                {/* Remove action */}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sleeves.map((sleeve) => (
              <tr
                key={sleeve.id}
                className={`hover:bg-gray-50 transition-colors ${
                  sleeve.is_sleeved ? 'bg-green-50' : ''
                }`}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={sleeve.is_sleeved}
                    onChange={() => handleToggleSleeve(sleeve.id, sleeve.is_sleeved)}
                    className="w-5 h-5 text-green-600 rounded focus:ring-2 focus:ring-green-500 cursor-pointer"
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="text-sm font-medium text-gray-900">
                    {sleeve.card_name || 'Standard Cards'}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-sm font-mono text-gray-700">
                    {sleeve.width_mm} × {sleeve.height_mm}
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="text-sm font-semibold text-gray-900">
                    {sleeve.quantity}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {sleeve.matched_product_name ? (
                    <div className="text-xs">
                      <span className="text-purple-700 font-medium">{sleeve.matched_product_name}</span>
                      <span className="text-gray-400 ml-1">
                        (stock: <span className={sleeve.matched_product_stock >= sleeve.quantity ? 'text-green-600' : 'text-red-500'}>
                          {sleeve.matched_product_stock}
                        </span>)
                      </span>
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400 italic">No match</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="text-xs text-gray-600">
                    {sleeve.notes || '—'}
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => handleDeleteSleeve(sleeve.id)}
                    title="Remove this sleeve requirement"
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {addFormPanel}

      {/* Summary */}
      <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
        <strong>Summary:</strong> {sleevedCount} of {sleeves.length} sleeve types marked as sleeved
      </div>
    </div>
  );
}
