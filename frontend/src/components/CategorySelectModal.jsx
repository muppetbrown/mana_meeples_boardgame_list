// src/components/CategorySelectModal.jsx
import React, { useRef, useEffect } from "react";
import { CATEGORY_KEYS, labelFor } from '../constants/categories';

export default function CategorySelectModal({ open, gameTitle, onSelect, onClose }) {
  const modalRef = useRef(null);
  const firstButtonRef = useRef(null);

  // Focus first button when modal opens
  useEffect(() => {
    if (open && firstButtonRef.current) {
      firstButtonRef.current.focus();
    }
  }, [open]);

  // Handle keyboard events
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e) => {
      // Close on Escape
      if (e.key === 'Escape') {
        onClose();
        return;
      }

      // Trap focus with Tab
      if (e.key === 'Tab') {
        const focusableElements = modalRef.current?.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const focusableArray = Array.from(focusableElements || []);
        const first = focusableArray[0];
        const last = focusableArray[focusableArray.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          last?.focus();
          e.preventDefault();
        } else if (!e.shiftKey && document.activeElement === last) {
          first?.focus();
          e.preventDefault();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  // Handle click outside to close
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl"
        role="document"
      >
        <h3 id="modal-title" className="text-xl font-bold mb-4">
          Select Category for "{gameTitle}"
        </h3>
        <div className="space-y-2">
          {CATEGORY_KEYS.map((c, index) => (
            <button
              key={c}
              ref={index === 0 ? firstButtonRef : null}
              className="w-full text-left px-4 py-3 rounded-lg border-2 border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition min-h-11 focus:outline-none focus:ring-2 focus:ring-purple-500"
              onClick={() => onSelect(c)}
              aria-label={`Assign to ${labelFor(c)} category`}
            >
              {labelFor(c)}
            </button>
          ))}
        </div>
        <button
          onClick={onClose}
          className="mt-4 w-full px-4 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 min-h-11 focus:outline-none focus:ring-2 focus:ring-gray-500"
          aria-label="Cancel and close dialog"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
