/**
 * Icon components for game card stat badges
 * Simple SVG icon components that can be passed to StatBadge
 */
import React from 'react';

export function UsersIcon({ className = '', ...props }) {
  return (
    <svg
      className={className}
      fill="currentColor"
      viewBox="0 0 20 20"
      {...props}
    >
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
    </svg>
  );
}

export function ClockIcon({ className = '', ...props }) {
  return (
    <svg
      className={className}
      fill="currentColor"
      viewBox="0 0 20 20"
      {...props}
    >
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
        clipRule="evenodd"
      />
    </svg>
  );
}

export function CalendarIcon({ className = '', ...props }) {
  return (
    <svg
      className={className}
      fill="currentColor"
      viewBox="0 0 20 20"
      {...props}
    >
      <path
        fillRule="evenodd"
        d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
        clipRule="evenodd"
      />
    </svg>
  );
}
