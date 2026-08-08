// frontend/src/components/public/FilterSheet.jsx
import React, { useEffect, useRef } from "react";
import { PLAYER_OPTIONS, TIME_OPTIONS, WEIGHT_OPTIONS } from "../../utils/libraryFilters";

function Pill({ active, onClick, children, ariaLabel }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={ariaLabel}
      style={{
        flexShrink: 0,
        borderRadius: 999,
        padding: "8px 13px",
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "'Source Sans 3', sans-serif",
        whiteSpace: "nowrap",
        minHeight: 40,
        minWidth: 52,
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 7,
        border: active ? "1.5px solid #3d5135" : "1.5px solid #d4e0d1",
        background: active ? "#3d5135" : "white",
        color: active ? "white" : "#3e473d",
      }}
    >
      {children}
    </button>
  );
}

/**
 * "Narrow it down" bottom sheet: players / duration / rules-crunch pill
 * groups. Every pill tap applies immediately to the shared filter state
 * (via the on* callbacks) — closing the sheet is just a UI convenience,
 * not a confirm step.
 */
export default function FilterSheet({
  open,
  onClose,
  players,
  onPlayersChange,
  time,
  onTimeChange,
  weight,
  onWeightChange,
  onClear,
  resultCount,
}) {
  const closeBtnRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    closeBtnRef.current?.focus();

    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const applyLabel = resultCount === 0 ? "No matches — loosen up" : `Show ${resultCount} game${resultCount === 1 ? "" : "s"}`;

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden="true"
        style={{ position: "fixed", inset: 0, background: "rgba(45,58,45,0.5)", zIndex: 90 }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="filter-sheet-title"
        style={{
          position: "fixed",
          left: "50%",
          transform: "translateX(-50%)",
          width: "100%",
          maxWidth: 414,
          boxSizing: "border-box",
          bottom: 0,
          zIndex: 100,
          background: "#fdfcf8",
          borderRadius: "22px 22px 0 0",
          boxShadow: "0 -8px 30px rgba(20,30,20,0.25)",
          maxHeight: "82vh",
          overflowY: "auto",
        }}
      >
        <div style={{ padding: "18px 20px 26px 20px", display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h2
              id="filter-sheet-title"
              style={{ fontFamily: "'Bricolage Grotesque', sans-serif", fontSize: 21, fontWeight: 800, color: "#3d5135", margin: 0, flex: 1 }}
            >
              Narrow it down
            </h2>
            <button
              ref={closeBtnRef}
              type="button"
              onClick={onClose}
              aria-label="Close filters"
              style={{ width: 44, height: 44, borderRadius: 999, border: "none", background: "#e8f0e4", color: "#3d5135", fontSize: 17, fontWeight: 700, cursor: "pointer" }}
            >
              ✕
            </button>
          </div>

          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "#3e473d", margin: "0 0 8px 0" }}>How many players?</p>
            <div role="group" aria-label="How many players?" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {PLAYER_OPTIONS.map((opt) => (
                <Pill key={opt} active={players === opt} onClick={() => onPlayersChange(players === opt ? "" : opt)}>
                  {opt}
                </Pill>
              ))}
            </div>
          </div>

          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "#3e473d", margin: "0 0 8px 0" }}>How long have you got?</p>
            <div role="group" aria-label="How long have you got?" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {TIME_OPTIONS.map(([val, label]) => (
                <Pill key={val} active={time === val} onClick={() => onTimeChange(time === val ? "" : val)}>
                  {label}
                </Pill>
              ))}
            </div>
          </div>

          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: "#3e473d", margin: "0 0 2px 0" }}>How much rules-crunch?</p>
            <p style={{ fontSize: 13, color: "#5f726c", margin: "0 0 8px 0" }}>Easy = learn in 5 minutes · Deep = a proper rules session</p>
            <div role="group" aria-label="How much rules-crunch?" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {WEIGHT_OPTIONS.map((opt) => (
                <Pill key={opt} active={weight === opt} onClick={() => onWeightChange(weight === opt ? "" : opt)}>
                  {opt}
                </Pill>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 4 }}>
            <button
              type="button"
              onClick={onClear}
              style={{ background: "none", border: "none", color: "#a35040", fontSize: 15, fontWeight: 700, fontFamily: "'Source Sans 3', sans-serif", cursor: "pointer", padding: 10 }}
            >
              Clear
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ flex: 1, minHeight: 54, background: "#3d5135", color: "white", border: "none", borderRadius: 999, fontSize: 16, fontWeight: 700, fontFamily: "'Source Sans 3', sans-serif", cursor: "pointer", boxShadow: "0 4px 14px rgba(61,81,53,0.35)" }}
            >
              {applyLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
