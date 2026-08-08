// src/components/public/GameCardPublic.jsx
// Mobile library redesign: horizontal card with cover, stat rows, Aftergame +
// expand actions, and an expandable details panel.
import React, { memo, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { labelFor } from "../../constants/categories";
import GameImage from "../GameImage";
import { getAfterGameCreateUrl } from "../../constants/aftergame";
import { getCategoryColor } from "../../utils/categoryStyles";
import {
  formatRating,
  formatComplexity,
  formatTime,
  formatPlayerCount,
  getComplexityBucket,
} from "../../utils/gameFormatters";

function getImageWithCacheBust(url, updatedAt) {
  if (!url) return null;
  const cacheBust = updatedAt ? new Date(updatedAt).getTime() : Date.now();
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${cacheBust}`;
}

function StatRow({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <span style={{ width: 58, flexShrink: 0, color: "#5f726c", fontWeight: 600 }}>{label}</span>
      <span style={{ color: "#3d5135", fontWeight: 700 }}>{value}</span>
    </div>
  );
}

const GameCardPublic = memo(function GameCardPublic({
  game,
  lazy = false,
  isExpanded = false,
  onToggleExpand,
  prefersReducedMotion = false,
  priority = false,
}) {
  const href = `/game/${game.id}`;
  const cardRef = useRef(null);

  const imgSrc = getImageWithCacheBust(game.cloudinary_url || game.image_url, game.updated_at);
  const categoryLabel = labelFor(game.mana_meeple_category);
  const categoryColor = getCategoryColor(game.mana_meeple_category);
  const playersText = formatPlayerCount(game) || "—";
  const timeText = formatTime(game.playtime_min, game.playtime_max);
  const weightBucket = getComplexityBucket(game.complexity);

  // Auto-scroll to top of card on mobile when expanded
  useEffect(() => {
    if (isExpanded && cardRef.current && window.innerWidth <= 768) {
      const timer = setTimeout(() => {
        cardRef.current?.scrollIntoView({
          behavior: prefersReducedMotion ? "auto" : "smooth",
          block: "nearest",
        });
      }, 100);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isExpanded, prefersReducedMotion]);

  return (
    <article
      ref={cardRef}
      data-game-card
      className="scroll-mt-24"
      style={{
        background: "white",
        borderRadius: 16,
        border: "1px solid #d4e0d1",
        overflow: "hidden",
        boxShadow: "0 2px 8px rgba(61,81,53,0.06)",
      }}
    >
      <div style={{ display: "flex", gap: 12, padding: 12 }}>
        <Link
          to={href}
          aria-label={`View details for ${game.title}`}
          style={{ display: "block", width: 104, height: 104, flexShrink: 0, borderRadius: 12, overflow: "hidden" }}
        >
          <GameImage
            url={imgSrc}
            alt={`Cover art for ${game.title}`}
            className="w-full h-full object-cover"
            fallbackClass="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-linear-to-br from-slate-100 to-slate-200"
            loading={lazy ? "lazy" : "eager"}
            fetchPriority={priority ? "high" : "auto"}
          />
        </Link>

        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 6 }}>
          <div>
            <h3
              style={{
                fontFamily: "'Bricolage Grotesque', sans-serif",
                fontSize: 17,
                fontWeight: 700,
                color: "#3e473d",
                lineHeight: 1.15,
                margin: "0 0 4px 0",
              }}
            >
              {game.title}
            </h3>
            {categoryLabel && (
              <span
                style={{
                  display: "inline-block",
                  padding: "3px 10px",
                  borderRadius: 999,
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.02em",
                  background: categoryColor,
                  color: "white",
                }}
              >
                {categoryLabel}
              </span>
            )}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: 13 }}>
            <StatRow label="Players" value={playersText} />
            <StatRow label="Time" value={timeText} />
            <StatRow label="Rules" value={weightBucket || "—"} />
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center", flexShrink: 0, padding: "2px 0" }}>
          <a
            href={getAfterGameCreateUrl(game.aftergame_game_id)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Organise a session on Aftergame"
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 44,
              height: 44,
              borderRadius: 999,
              background: "white",
              border: "1.5px solid #d3daf7",
              boxShadow: "0 1px 4px rgba(61,81,53,0.08)",
            }}
          >
            <img src="/Aftergame_Icon_Logo_V3-Light.webp" alt="" style={{ width: 24, height: 24 }} />
          </a>
          <button
            type="button"
            onClick={onToggleExpand}
            aria-label={isExpanded ? "Show less" : "More info"}
            aria-expanded={isExpanded}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 44,
              height: 44,
              borderRadius: 999,
              border: "1.5px solid #d4e0d1",
              background: isExpanded ? "#e8f0e4" : "white",
              color: "#3d5135",
              cursor: "pointer",
            }}
          >
            <svg
              width="17"
              height="17"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
              aria-hidden="true"
              style={{ transform: isExpanded ? "rotate(180deg)" : "none", transition: prefersReducedMotion ? "none" : "transform 0.25s" }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {isExpanded && (
        <div style={{ padding: "14px 16px 16px 16px", borderTop: "1px solid #e8f0e4", display: "flex", flexDirection: "column", gap: 10 }}>
          {game.description && (
            <p className="line-clamp-4" style={{ fontSize: 14, color: "#5f726c", lineHeight: 1.55, margin: 0 }}>
              {game.description}
            </p>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 12px", fontSize: 14, color: "#3e473d" }}>
            {game.designers && game.designers.length > 0 && (
              <span>
                <strong>Designer{game.designers.length > 1 ? "s" : ""}</strong>
                <br />
                {game.designers.slice(0, 2).join(", ")}
                {game.designers.length > 2 && ` +${game.designers.length - 2} more`}
              </span>
            )}
            {formatRating(game.average_rating) && (
              <span>
                <strong>BGG rating</strong>
                <br />★ {formatRating(game.average_rating)} / 10
              </span>
            )}
            {formatComplexity(game.complexity) && (
              <span>
                <strong>Complexity</strong>
                <br />
                {formatComplexity(game.complexity)} / 5{weightBucket ? ` · ${weightBucket}` : ""}
              </span>
            )}
            {game.year && (
              <span>
                <strong>Published</strong>
                <br />
                {game.year}
              </span>
            )}
          </div>
          <Link
            to={href}
            style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "#3d5135", fontWeight: 700, fontSize: 14, textDecoration: "none", marginTop: 2 }}
          >
            View full details <span aria-hidden="true">→</span>
          </Link>
        </div>
      )}
    </article>
  );
}, (prevProps, nextProps) => (
  prevProps.game.id === nextProps.game.id &&
  prevProps.isExpanded === nextProps.isExpanded &&
  prevProps.lazy === nextProps.lazy &&
  prevProps.priority === nextProps.priority &&
  prevProps.prefersReducedMotion === nextProps.prefersReducedMotion
));

export default GameCardPublic;
