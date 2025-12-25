import React from "react";

export default function SearchBox({ value, onChange, placeholder="Search games...", id, className, ...props }) {
  return (
    <input
      id={id}
      className={className || "w-full min-h-[44px] px-4 py-3 text-base border-2 border-slate-300 rounded-xl focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 focus:outline-none transition-all bg-white touch-manipulation"}
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      autoComplete="off"
      spellCheck="false"
      role="searchbox"
      {...props}
    />
  );
}
