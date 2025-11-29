// src/components/common/LoadingSpinner.jsx
/**
 * Shared loading spinner component
 * Provides consistent loading states across the application
 */
import React from 'react';

/**
 * LoadingSpinner - Animated spinner with optional text
 *
 * @param {Object} props
 * @param {'sm'|'md'|'lg'} props.size - Size of the spinner
 * @param {string} props.text - Optional text to display below spinner
 * @param {string} props.className - Additional CSS classes
 */
export function LoadingSpinner({ size = 'md', text, className = '' }) {
  const sizes = {
    sm: 'w-6 h-6',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-4 p-8 ${className}`}>
      <div
        className={`${sizes[size]} border-4 border-amber-200 border-t-amber-600 rounded-full animate-spin`}
        role="status"
        aria-label={text || 'Loading'}
      />
      {text && <p className="text-slate-600 text-sm">{text}</p>}
      <span className="sr-only">{text || 'Loading...'}</span>
    </div>
  );
}

/**
 * FullPageLoader - Loading spinner that fills the entire page
 */
export function FullPageLoader({ text = 'Loading...' }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <LoadingSpinner size="lg" text={text} />
    </div>
  );
}

/**
 * InlineLoader - Compact loading indicator for inline use
 */
export function InlineLoader({ text }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-4 h-4 border-2 border-amber-200 border-t-amber-600 rounded-full animate-spin" />
      {text && <span className="text-sm text-slate-600">{text}</span>}
    </div>
  );
}

export default LoadingSpinner;
