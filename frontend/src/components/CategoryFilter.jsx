import React from "react";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../constants/categories";

export default function CategoryFilter({ selected, counts, onChange }) {
  // All category values in order
  const allCategories = ['all', ...CATEGORY_KEYS, 'uncategorized'];

  // Handle keyboard navigation with arrow keys
  const handleKeyNav = (e, currentValue) => {
    const currentIndex = allCategories.indexOf(currentValue);

    if (e.key === 'ArrowRight' && currentIndex < allCategories.length - 1) {
      e.preventDefault();
      onChange(allCategories[currentIndex + 1]);
    } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
      e.preventDefault();
      onChange(allCategories[currentIndex - 1]);
    }
  };

  const Chip = ({ value, label }) => (
    <button
      type="button"
      onClick={() => onChange(value)}
      onKeyDown={(e) => handleKeyNav(e, value)}
      aria-label={`Filter by ${label}`}
      aria-pressed={selected === value}
      tabIndex={selected === value ? 0 : -1}
      className={
        "px-3 py-1 rounded-full text-sm border transition min-h-11 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 " +
        (selected === value
          ? "bg-purple-600 text-white border-purple-600"
          : "bg-white text-gray-700 border-gray-300 hover:border-purple-400")
      }
    >
      {label}
      <span className="ml-2 inline-block px-2 py-0.5 rounded-full bg-gray-100 text-gray-700" aria-label={`${counts?.[value] ?? 0} games`}>
        {counts?.[value] ?? 0}
      </span>
    </button>
  );

  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Category filters">
      <Chip value="all" label="All Games" />
      {CATEGORY_KEYS.map((k) => (
        <Chip key={k} value={k} label={CATEGORY_LABELS[k]} />
      ))}
      <Chip value="uncategorized" label="Uncategorized" />
    </div>
  );
}
