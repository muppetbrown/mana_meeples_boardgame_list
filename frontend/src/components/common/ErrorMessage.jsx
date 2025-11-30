import React from "react";

/**
 * User-friendly error message component with retry capability
 * Provides clear, actionable error messages with optional retry button
 */
export default function ErrorMessage({ error, onRetry, className = "" }) {
  // Map error codes to user-friendly messages
  const errorMessages = {
    'NETWORK_ERROR': 'Connection problem. Please check your internet and try again.',
    'BGG_FETCH_FAILED': "Couldn't load game from BoardGameGeek. Try again in a moment.",
    'GAME_NOT_FOUND': 'Game not found. It may have been removed.',
    'UNAUTHORIZED': 'Admin access required. Please log in.',
    'VALIDATION_ERROR': 'Please check your input and try again.',
    'SERVER_ERROR': 'Server error. Please try again later.',
  };

  // Determine the message to display
  const getMessage = () => {
    if (!error) return 'An unexpected error occurred';

    // If error is a string, use it directly
    if (typeof error === 'string') return error;

    // If error has a code, look up the friendly message
    if (error.code && errorMessages[error.code]) {
      return errorMessages[error.code];
    }

    // If error has a message property, use it
    if (error.message) return error.message;

    // Default fallback
    return 'Something went wrong. Please try again.';
  };

  const message = getMessage();
  const showRetry = typeof onRetry === 'function';

  return (
    <div
      className={`bg-red-50 border-l-4 border-red-500 p-4 rounded ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start">
        {/* Error Icon */}
        <svg
          className="w-6 h-6 text-red-500 mr-3 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>

        {/* Error Content */}
        <div className="flex-1">
          <h3 className="text-red-800 font-semibold text-sm">Error</h3>
          <p className="text-red-700 mt-1 text-sm">{message}</p>

          {/* Retry Button */}
          {showRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-sm text-red-700 underline hover:text-red-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 rounded transition-colors"
              aria-label="Retry the failed operation"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Inline error message for form fields
 */
export function InlineError({ message, className = "" }) {
  if (!message) return null;

  return (
    <p
      className={`text-red-600 text-sm mt-1 flex items-center ${className}`}
      role="alert"
    >
      <svg
        className="w-4 h-4 mr-1 flex-shrink-0"
        fill="currentColor"
        viewBox="0 0 20 20"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
          clipRule="evenodd"
        />
      </svg>
      {message}
    </p>
  );
}

/**
 * Empty state component for when no results are found
 */
export function EmptyState({ title, message, action }) {
  return (
    <div className="text-center py-12 px-4">
      <svg
        className="mx-auto h-12 w-12 text-slate-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
        />
      </svg>
      <h3 className="mt-4 text-lg font-medium text-slate-900">{title}</h3>
      {message && <p className="mt-2 text-sm text-slate-600">{message}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
