import React from 'react';

export default function SleeveShoppingListModal({ shoppingList, onClose }) {
  if (!shoppingList) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b">
          <h2 className="text-2xl font-bold">Sleeve Shopping List</h2>
        </div>
        
        <div className="p-6 overflow-y-auto flex-1">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Size (mm)</th>
                <th className="border p-2 text-right">Total Quantity</th>
                <th className="border p-2 text-right">Games</th>
                <th className="border p-2 text-right">Variations</th>
                <th className="border p-2 text-left">Game Names</th>
              </tr>
            </thead>
            <tbody>
              {shoppingList.map((item, idx) => (
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
                  <td className="border p-2 text-right">
                    {item.variations_grouped > 1 && (
                      <span className="text-orange-600 font-semibold">
                        {item.variations_grouped}
                      </span>
                    )}
                    {item.variations_grouped === 1 && '—'}
                  </td>
                  <td className="border p-2 text-sm text-gray-600">
                    {item.game_names.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          <div className="mt-4 p-4 bg-blue-50 rounded">
            <p className="text-sm">
              <strong>Note:</strong> "Variations" indicates slight size differences that have been grouped together.
              Double-check sleeve compatibility for items with variations &gt; 1.
            </p>
          </div>
        </div>
        
        <div className="p-6 border-t flex justify-between">
          <button
            onClick={() => {
              // Generate CSV
              const csv = generateCSV(shoppingList);
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

function generateCSV(shoppingList) {
  const rows = [
    ['Size (mm)', 'Total Quantity', 'Games Count', 'Variations', 'Game Names']
  ];
  
  shoppingList.forEach(item => {
    rows.push([
      `${item.width_mm}x${item.height_mm}`,
      item.total_quantity,
      item.games_count,
      item.variations_grouped,
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