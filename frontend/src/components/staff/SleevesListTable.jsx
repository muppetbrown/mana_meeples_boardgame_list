import React, { useState, useEffect } from 'react';
import { getGameSleeves, updateSleeveStatus } from '../../api/client';

export default function SleevesListTable({ gameId, onSleeveUpdate }) {
  const [sleeves, setSleeves] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stockFeedback, setStockFeedback] = useState(null);

  useEffect(() => {
    loadSleeves();
  }, [gameId]);

  const loadSleeves = async () => {
    setLoading(true);
    try {
      const data = await getGameSleeves(gameId);
      setSleeves(data);
    } catch (error) {
      console.error('Failed to load sleeves:', error);
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

  const fullySleeved = sleeves.length > 0 && sleeves.every(s => s.is_sleeved);
  const sleevedCount = sleeves.filter(s => s.is_sleeved).length;

  if (loading) {
    return <div className="text-center py-4">Loading sleeve requirements...</div>;
  }

  if (sleeves.length === 0) {
    return (
      <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
        <p className="text-sm text-gray-700">
          No sleeve requirements defined for this game.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
        <strong>Summary:</strong> {sleevedCount} of {sleeves.length} sleeve types marked as sleeved
      </div>
    </div>
  );
}
