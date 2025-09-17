import React from "react";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../constants/categories";

export default function CategoryFilter({ selected, counts, onChange }) {
  const Chip = ({ value, label }) => (
    <button
      type="button"
      onClick={() => onChange(value)}
      className={
        "px-3 py-1 rounded-full text-sm border transition " +
        (selected === value
          ? "bg-purple-600 text-white border-purple-600"
          : "bg-white text-gray-700 border-gray-300 hover:border-purple-400")
      }
    >
      {label}
      <span className="ml-2 inline-block px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
        {counts?.[value] ?? 0}
      </span>
    </button>
  );

  return (
    <div className="flex flex-wrap gap-2">
      <Chip value="all" label="All Games" />
      {CATEGORY_KEYS.map((k) => (
        <Chip key={k} value={k} label={CATEGORY_LABELS[k]} />
      ))}
      <Chip value="uncategorized" label="Uncategorized" />
    </div>
  );
}
