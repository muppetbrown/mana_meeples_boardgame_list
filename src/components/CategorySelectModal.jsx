// src/components/CategorySelectModal.jsx
import React from "react";
import { CATEGORY_KEYS, labelFor } from '../constants/categories';

export default function CategorySelectModal({ open, gameTitle, onSelect, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl">
        <h3 className="text-xl font-bold mb-4">Select Category for “{gameTitle}”</h3>
        <div className="space-y-2">
          {CATEGORY_KEYS.map((c) => (
            <button
              key={c}
              className="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition"
              onClick={() => onSelect(c)}
            >
              {labelFor(c)}
            </button>
          ))}
        </div>
        <button
          onClick={onClose}
          className="mt-4 w-full px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
