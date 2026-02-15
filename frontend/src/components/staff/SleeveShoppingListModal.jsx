import React, { useState, useEffect } from 'react';
import { getSleeveProducts } from '../../api/client';

export default function SleeveShoppingListModal({ shoppingList, onClose }) {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    if (shoppingList) {
      getSleeveProducts().then(setProducts).catch(() => setProducts([]));
    }
  }, [shoppingList]);

  if (!shoppingList) return null;

  // Match each shopping list size to a product
  // Tolerances must match backend: services/sleeve_matching.py (WIDTH_TOLERANCE_MM=1, HEIGHT_TOLERANCE_MM=5)
  const findMatch = (width, height) => {
    return products.find(
      (p) =>
        p.width_mm >= width &&
        p.width_mm <= width + 1 &&
        p.height_mm >= height &&
        p.height_mm <= height + 5
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b">
          <h2 className="text-2xl font-bold">Sleeve Shopping List</h2>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Size (mm)</th>
                <th className="border p-2 text-right">Total Qty</th>
                <th className="border p-2 text-right">Games</th>
                <th className="border p-2 text-left">Matched Product</th>
                <th className="border p-2 text-right">Stock</th>
                <th className="border p-2 text-right">Price/Pack</th>
                <th className="border p-2 text-left">Game Names</th>
              </tr>
            </thead>
            <tbody>
              {shoppingList.map((item, idx) => {
                const match = findMatch(item.width_mm, item.height_mm);
                return (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="border p-2 font-mono">
                      {item.width_mm} × {item.height_mm}
                    </td>
                    <td className="border p-2 text-right font-bold">
                      {item.total_quantity}
                    </td>
                    <td className="border p-2 text-right">
                      {item.games_count}
                    </td>
                    <td className="border p-2">
                      {match ? (
                        <div className="text-xs">
                          <div className="font-medium text-purple-700">{match.name}</div>
                          <div className="text-gray-500">{match.distributor}</div>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 italic">No match</span>
                      )}
                    </td>
                    <td className="border p-2 text-right">
                      {match ? (
                        <span className={match.in_stock >= item.total_quantity ? 'text-green-600 font-semibold' : 'text-red-500'}>
                          {match.in_stock}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="border p-2 text-right">
                      {match ? `$${match.price.toFixed(2)}` : '—'}
                    </td>
                    <td className="border p-2 text-sm text-gray-600">
                      {item.game_names.join(', ')}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="mt-4 p-4 bg-blue-50 rounded">
            <p className="text-sm">
              <strong>Note:</strong> Product matches use tolerance: width +0-1mm, height +0-5mm.
              Run "Auto-Match" in the Sleeve Inventory tab to persist matches.
            </p>
          </div>
        </div>

        <div className="p-6 border-t flex justify-between">
          <button
            onClick={() => {
              const csv = generateCSV(shoppingList, products, findMatch);
              downloadCSV(csv, 'sleeve-shopping-list.csv');
            }}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            Download CSV
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function generateCSV(shoppingList, products, findMatch) {
  const rows = [
    ['Size (mm)', 'Total Quantity', 'Games Count', 'Product', 'Distributor', 'Stock', 'Price/Pack', 'Game Names']
  ];

  shoppingList.forEach(item => {
    const match = findMatch(item.width_mm, item.height_mm);
    rows.push([
      `${item.width_mm}x${item.height_mm}`,
      item.total_quantity,
      item.games_count,
      match ? match.name : '',
      match ? match.distributor : '',
      match ? match.in_stock : '',
      match ? match.price : '',
      item.game_names.join('; ')
    ]);
  });

  return rows.map(row => row.join(',')).join('\n');
}

function downloadCSV(csv, filename) {
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}
