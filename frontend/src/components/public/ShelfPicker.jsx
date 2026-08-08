// frontend/src/components/public/ShelfPicker.jsx
import React from "react";
import { CATEGORY_LABELS } from "../../constants/categories";
import { getCategoryColor } from "../../utils/categoryStyles";

/**
 * Display order for the shelf picker's game-box category toggles.
 * Deliberately separate from CATEGORY_KEYS (constants/categories.js) so the
 * staff/admin category ordering elsewhere in the app is unaffected.
 */
export const SHELF_ORDER = [
  "KIDS_FAMILIES",
  "PARTY_ICEBREAKERS",
  "GATEWAY_STRATEGY",
  "COOP_ADVENTURE",
  "CORE_STRATEGY",
];

const RAIL_STYLE = {
  height: 7,
  background: "linear-gradient(#c9b285, #a8905f)",
  borderRadius: 3,
  boxShadow: "0 3px 4px rgba(61,81,53,0.18)",
};

function ShelfBox({ categoryKey, count, active, onToggle }) {
  const color = getCategoryColor(categoryKey);
  const label = CATEGORY_LABELS[categoryKey] || categoryKey;

  return (
    <button
      type="button"
      onClick={() => onToggle(categoryKey)}
      aria-pressed={active}
      aria-label={`${label}, ${count ?? 0} games`}
      style={{
        position: "relative",
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 2,
        padding: "10px 10px 8px 10px",
        minHeight: 64,
        textAlign: "left",
        cursor: "pointer",
        fontFamily: "'Source Sans 3', sans-serif",
        color: "white",
        background: color,
        border: "none",
        borderRadius: "9px 9px 3px 3px",
        boxShadow: active
          ? "0 10px 16px rgba(61,81,53,0.35), inset 0 0 0 2px rgba(255,255,255,0.85)"
          : "inset 0 -5px 0 rgba(0,0,0,0.18)",
        transform: active ? "translateY(-7px)" : "none",
        transition: "transform 0.18s, box-shadow 0.18s",
      }}
    >
      {active && (
        <span
          aria-hidden="true"
          style={{
            position: "absolute",
            top: -7,
            right: -5,
            width: 20,
            height: 20,
            borderRadius: 999,
            background: "white",
            color,
            fontSize: 12,
            fontWeight: 800,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 1px 4px rgba(61,81,53,0.3)",
          }}
        >
          ✓
        </span>
      )}
      <span style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 13, fontWeight: 700, lineHeight: 1.15 }}>
        {label}
      </span>
      <span style={{ fontSize: 11, fontWeight: 600, opacity: 0.85 }}>
        {count ?? 0} games
      </span>
    </button>
  );
}

/**
 * "Or browse the shelves" category picker: two wooden shelf rails with
 * game-box toggle buttons. Multi-select; none selected means all games.
 *
 * @param {Object} counts - category-counts response, e.g. { KIDS_FAMILIES: 34, ... }
 * @param {string[]} selected - currently selected category keys
 * @param {(key: string) => void} onToggle - toggle a category key
 */
export default function ShelfPicker({ counts, selected, onToggle }) {
  const row1 = SHELF_ORDER.slice(0, 3);
  const row2 = SHELF_ORDER.slice(3);

  return (
    <section id="shelf-picker" style={{ padding: "14px 20px 10px 20px" }}>
      <h2 style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 17, fontWeight: 700, color: "#3d5135", margin: "0 0 2px 0" }}>
        Or browse the shelves
      </h2>
      <p style={{ fontSize: 13, color: "#5f726c", margin: "0 0 12px 0" }}>
        Tap a box to take it off the shelf — mix as many as you like.
      </p>

      <div
        role="group"
        aria-label="Filter by category, row 1"
        style={{ display: "flex", alignItems: "flex-end", gap: 8, padding: "0 6px" }}
      >
        {row1.map((key) => (
          <ShelfBox key={key} categoryKey={key} count={counts?.[key]} active={selected.includes(key)} onToggle={onToggle} />
        ))}
      </div>
      <div style={{ ...RAIL_STYLE, marginBottom: 12 }} aria-hidden="true" />

      <div
        role="group"
        aria-label="Filter by category, row 2"
        style={{ display: "flex", alignItems: "flex-end", gap: 8, padding: "0 6px", justifyContent: "center" }}
      >
        {row2.map((key) => (
          <ShelfBox key={key} categoryKey={key} count={counts?.[key]} active={selected.includes(key)} onToggle={onToggle} />
        ))}
      </div>
      <div style={RAIL_STYLE} aria-hidden="true" />
    </section>
  );
}
