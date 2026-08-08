// frontend/src/utils/libraryFilters.js
/**
 * Shared filter definitions and API-param mapping for the mobile library
 * redesign (PublicCatalogue quick-picks, shelf picker and filter sheet).
 */

export const QUICK_PICKS = [
  { key: "first", icon: "🎲", label: "First timers", sub: "Learn in minutes, any shelf" },
  { key: "kids", icon: "🪸", label: "With the kids", sub: "Simple rules, family fun" },
  { key: "group", icon: "🎉", label: "Big group", sub: "Plays well with 6+" },
  { key: "coop", icon: "🤝", label: "Team up", sub: "Win (or lose) together" },
];

export const PLAYER_OPTIONS = ["1", "2", "3", "4", "5", "6+"];

export const TIME_OPTIONS = [
  ["quick", "Under 30 min"],
  ["mid", "30–60 min"],
  ["long", "Over an hour"],
];

export const WEIGHT_OPTIONS = ["Easy", "Light", "Medium", "Deep"];

/**
 * Map the sheet's player pill value to the API's `players` param.
 * '6+' approximates "plays 6 or more" using the existing fits-at-table filter.
 */
export function playersToParam(players) {
  if (!players) return undefined;
  if (players === "6+") return 6;
  const n = parseInt(players, 10);
  return Number.isNaN(n) ? undefined : n;
}

/** Map the sheet's duration bucket to playtime_max_min/playtime_max_max params. */
export function timeToPlaytimeParams(time) {
  switch (time) {
    case "quick":
      return { playtime_max_max: 30 };
    case "mid":
      return { playtime_max_min: 31, playtime_max_max: 60 };
    case "long":
      return { playtime_max_min: 61 };
    default:
      return {};
  }
}

/**
 * Map the sheet's rules-crunch bucket to complexity_min/complexity_max params.
 * Boundaries mirror utils/gameFormatters.js#getComplexityBucket.
 */
export function weightToComplexityParams(weight) {
  switch (weight) {
    case "Easy":
      return { complexity_max: 1.4999 };
    case "Light":
      return { complexity_min: 1.5, complexity_max: 2.1999 };
    case "Medium":
      return { complexity_min: 2.2, complexity_max: 2.9999 };
    case "Deep":
      return { complexity_min: 3 };
    default:
      return {};
  }
}

export function timeLabel(time) {
  const found = TIME_OPTIONS.find(([val]) => val === time);
  return found ? found[1] : "";
}
