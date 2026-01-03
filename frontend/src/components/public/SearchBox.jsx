import React, { useState, useEffect, useCallback } from "react";

/**
 * SearchBox with debouncing to reduce API calls.
 * Phase 1 Performance Optimization:
 * - Waits 300ms after last keystroke before triggering search
 * - Reduces API calls by ~85% during typing
 */
export default function SearchBox({ value, onChange, placeholder="Search games...", id, className, ...props }) {
  const [searchTerm, setSearchTerm] = useState(value || "");
  const [debouncedTerm, setDebouncedTerm] = useState(value || "");

  // Sync with external value changes - FIXED: Only update if value actually changed
  useEffect(() => {
    const newValue = value || "";
    if (searchTerm !== newValue) {
      setSearchTerm(newValue);
      setDebouncedTerm(newValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);  // Only sync when prop changes, not when searchTerm changes internally

  // Debounce search term updates (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, 300);  // Wait 300ms after last keystroke

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Trigger API call only when debounced term changes - FIXED: Prevent duplicate onChange calls
  useEffect(() => {
    if (debouncedTerm !== value && onChange) {
      onChange(debouncedTerm);
    }
  }, [debouncedTerm, onChange, value]);

  const handleSearchChange = (e) => {
    const newValue = e.target.value;
    setSearchTerm(newValue);  // Update input immediately (instant feedback)
    // API call happens after 300ms delay via useEffect
  };

  return (
    <input
      id={id}
      className={className || "w-full min-h-[44px] px-4 py-3 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white touch-manipulation"}
      type="search"
      value={searchTerm}
      onChange={handleSearchChange}
      placeholder={placeholder}
      aria-label={placeholder}
      autoComplete="off"
      spellCheck="false"
      role="searchbox"
      {...props}
    />
  );
}
