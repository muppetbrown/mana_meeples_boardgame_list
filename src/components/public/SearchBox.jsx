import React from "react";

export default function SearchBox({ value, onChange, placeholder="Search games..." }) {
  return (
    <input
      className="border rounded px-3 py-2 w-full"
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  );
}
