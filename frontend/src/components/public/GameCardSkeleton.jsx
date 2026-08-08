// src/components/public/GameCardSkeleton.jsx
import React from "react";

/**
 * Skeleton loader for GameCardPublic (mobile library redesign).
 * Matches the redesigned card's dimensions (104x104 cover, 3 stat rows,
 * action column) to prevent layout shift while games are loading.
 */
export default function GameCardSkeleton() {
  return (
    <article
      className="animate-pulse"
      aria-hidden="true"
      style={{ background: "white", borderRadius: 16, border: "1px solid #d4e0d1", overflow: "hidden", boxShadow: "0 2px 8px rgba(61,81,53,0.06)" }}
    >
      <div style={{ display: "flex", gap: 12, padding: 12 }}>
        <div style={{ width: 104, height: 104, flexShrink: 0, borderRadius: 12, background: "#e8f0e4" }} />

        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ height: 17, width: "70%", borderRadius: 4, background: "#e8f0e4" }} />
          <div style={{ height: 18, width: 90, borderRadius: 999, background: "#f0f2e8" }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ height: 11, width: "60%", borderRadius: 4, background: "#f0f2e8" }} />
            <div style={{ height: 11, width: "50%", borderRadius: 4, background: "#f0f2e8" }} />
            <div style={{ height: 11, width: "55%", borderRadius: 4, background: "#f0f2e8" }} />
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center", flexShrink: 0, padding: "2px 0" }}>
          <div style={{ width: 44, height: 44, borderRadius: 999, background: "#f0f2e8" }} />
          <div style={{ width: 44, height: 44, borderRadius: 999, background: "#f0f2e8" }} />
        </div>
      </div>
    </article>
  );
}
