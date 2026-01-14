/**
 * GameCardStats - Reusable 2x2 stats grid for game cards
 * Includes Players, Time, Complexity stats and Expand button
 * Used in both collapsed and expanded views of GameCardPublic
 */
import React from 'react';
import { formatComplexity, formatTime, formatPlayerCount } from '../../../utils/gameFormatters';

// SVG Icon Components (inline to avoid extra imports)
function UsersIcon({ className }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
    </svg>
  );
}

function ClockIcon({ className }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ChevronIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

/**
 * PlayersBadge - Displays player count with users icon
 */
function PlayersBadge({ game }) {
  const playerCount = formatPlayerCount(game);

  return (
    <div
      className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
      aria-label={playerCount ? `${playerCount} players` : 'Player count not available'}
    >
      <UsersIcon className="w-3.5 h-3.5 md:w-4 md:h-4 text-emerald-600" />
      <span className="font-semibold text-xs md:text-sm text-slate-700">
        {playerCount || '—'}
      </span>
    </div>
  );
}

/**
 * TimeBadge - Displays play time with clock icon
 */
function TimeBadge({ game }) {
  const timeDisplay = formatTime(game.playtime_min, game.playtime_max);

  return (
    <div
      className="flex flex-col items-center justify-center gap-0.5 md:gap-1 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
      aria-label={`Play time: ${timeDisplay}`}
    >
      <ClockIcon className="w-3.5 h-3.5 md:w-4 md:h-4 text-slate-500" />
      <span className="font-semibold text-xs md:text-sm text-slate-700">
        {timeDisplay}
      </span>
    </div>
  );
}

/**
 * ComplexityBadge - Displays complexity rating with puzzle emoji
 */
function ComplexityBadge({ game }) {
  const complexity = formatComplexity(game.complexity);
  const hasComplexity = Boolean(complexity);

  return (
    <div
      className="flex flex-col items-center justify-center gap-0.5 bg-slate-50 rounded-lg py-1.5 md:py-2 px-1"
      aria-label={hasComplexity ? `Complexity: ${complexity} out of 5` : 'Complexity not available'}
    >
      <span className={`text-[9px] md:text-[10px] font-bold uppercase tracking-wide ${hasComplexity ? 'text-amber-600' : 'text-slate-400'}`}>
        Complexity
      </span>
      <span className={`font-semibold text-xs md:text-sm ${hasComplexity ? 'text-slate-700' : 'text-slate-400'}`}>
        {hasComplexity ? `🧩 ${complexity}/5` : '🧩 —'}
      </span>
    </div>
  );
}

/**
 * ExpandButton - Toggle button for expand/collapse
 */
function ExpandButton({ isExpanded, onToggle, showHint = false, variant = 'collapsed' }) {
  const baseClasses = "flex flex-col items-center justify-center gap-0.5 md:gap-1 rounded-lg py-1.5 md:py-2 px-1 text-xs font-bold transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500";

  const variantClasses = variant === 'expanded'
    ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
    : isExpanded
      ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-200 border-emerald-300 border-2 shadow-sm hover:shadow-md"
      : "bg-linear-to-br from-emerald-50 to-teal-50 text-emerald-700 hover:from-emerald-100 hover:to-teal-100 border-emerald-200 hover:border-emerald-300 border-2 shadow-sm hover:shadow-md";

  const hintClasses = showHint && !isExpanded ? 'animate-pulse ring-2 ring-emerald-500' : '';

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${hintClasses}`}
      aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
      aria-expanded={isExpanded}
      onClick={(e) => {
        e.stopPropagation();
        onToggle();
      }}
    >
      <ChevronIcon
        className={`w-4 h-4 md:w-5 md:h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
      />
      <span className="text-[10px] md:text-xs font-bold">
        {isExpanded ? 'Less' : 'More'}
      </span>
    </button>
  );
}

/**
 * GameCardStats - Complete 2x2 stats grid
 * @param {Object} game - Game data object
 * @param {boolean} isExpanded - Whether card is expanded
 * @param {function} onToggleExpand - Callback to toggle expansion
 * @param {boolean} showHint - Whether to show onboarding hint on expand button
 * @param {string} variant - 'collapsed' or 'expanded' for styling differences
 * @param {string} className - Additional CSS classes
 */
export function GameCardStats({
  game,
  isExpanded = false,
  onToggleExpand,
  showHint = false,
  variant = 'collapsed',
  className = ''
}) {
  return (
    <div className={`grid grid-cols-2 gap-1.5 md:gap-2 ${className}`}>
      <PlayersBadge game={game} />
      <TimeBadge game={game} />
      <ComplexityBadge game={game} />
      <ExpandButton
        isExpanded={isExpanded}
        onToggle={onToggleExpand}
        showHint={showHint}
        variant={variant}
      />
    </div>
  );
}

export default GameCardStats;
