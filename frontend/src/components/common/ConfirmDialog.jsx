// src/components/common/ConfirmDialog.jsx
/**
 * In-app replacement for window.confirm. Optionally requires the user to type
 * a phrase before a destructive action can be confirmed.
 */
import React, { useState } from "react";
import Modal from "./Modal";

export function ConfirmDialog({
  title = "Are you sure?",
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "default", // 'default' | 'danger'
  requireText,
  onConfirm,
  onCancel,
}) {
  const [typed, setTyped] = useState("");
  const canConfirm = !requireText || typed.trim().toLowerCase() === requireText.toLowerCase();
  const confirmStyle =
    tone === "danger"
      ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
      : "bg-purple-600 hover:bg-purple-700 focus:ring-purple-500";

  return (
    <Modal onClose={onCancel} labelledBy="confirm-title" maxWidth="max-w-md">
      <form
        className="p-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (canConfirm) onConfirm();
        }}
      >
        <h2 id="confirm-title" className="text-lg font-semibold text-gray-900 mb-2">
          {title}
        </h2>
        {message && <p className="text-sm text-gray-600 whitespace-pre-line mb-4">{message}</p>}
        {requireText && (
          <div className="mb-4">
            <label htmlFor="confirm-phrase" className="block text-sm text-gray-700 mb-1">
              Type <strong>{requireText}</strong> to confirm
            </label>
            <input
              id="confirm-phrase"
              type="text"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
              className="w-full border-2 border-gray-300 focus:border-red-500 rounded-lg px-3 py-2 outline-none"
            />
          </div>
        )}
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg border-2 border-gray-300 text-gray-700 font-medium hover:bg-gray-50"
          >
            {cancelLabel}
          </button>
          <button
            type="submit"
            disabled={!canConfirm}
            className={`px-4 py-2 rounded-lg text-white font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${confirmStyle}`}
          >
            {confirmLabel}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default ConfirmDialog;
