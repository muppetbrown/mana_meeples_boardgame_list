// src/utils/libraryQuality.js
/**
 * "Needs attention" checks for owned games, shared by the Dashboard
 * (counts) and Manage Library (filtering).
 */
export const SLEEVE_UNKNOWN = (g) =>
  !g.has_sleeves || g.has_sleeves === "not_found" || g.has_sleeves === "check" || g.has_sleeves === "error";

// Has known sleeve requirements ('found' / 'manual') that aren't all sleeved yet.
// Games with no sleeve needs ('none') and games whose status is still unknown
// are excluded - those have their own checks.
export const TO_BE_SLEEVED = (g) =>
  (g.has_sleeves === "found" || g.has_sleeves === "manual") && !g.fully_sleeved;

/**
 * Each check carries admin-facing guidance:
 *  - hint:  one line shown on the Dashboard card
 *  - fix:   { why, steps[] } shown as "How to fix this" in Manage Library
 */
export const ATTENTION_FILTERS = [
  {
    key: "uncategorized",
    label: "Uncategorized",
    test: (g) => !g.mana_meeple_category,
    tab: "categories",
    hint: "Give each game one of the 5 categories.",
    fix: {
      why: "Games without a category don't show up under the public category filters.",
      steps: [
        "Use the Category dropdown on each row below. It saves as soon as you pick one.",
        "For a big batch, open the Categories tab and use Bulk Categorize from CSV (bgg_id,category).",
      ],
    },
  },
  {
    key: "sleeves_unknown",
    label: "Sleeve status unknown",
    test: SLEEVE_UNKNOWN,
    hint: "Fetch sleeve data, or mark \"no sleeves needed\".",
    fix: {
      why: "We don't yet know whether these games have cards that need sleeving (❓🃏), so they can't appear on shopping lists.",
      steps: [
        "Select the games (Select All works), then click Fetch Sleeve Data. It runs in the background and may take a few minutes; progress shows beside the buttons.",
        "Games with no cards (dice games, etc.): click Edit Game → Sleeves tab → Mark No Sleeves Needed.",
        "If the fetch finds nothing for a game, open Edit Game → Sleeves tab → + Add Sleeve Requirement and enter the card sizes by hand.",
        "A status of \"error\" just means the scraper failed. Run Fetch Sleeve Data again.",
      ],
    },
  },
  {
    key: "to_sleeve",
    label: "Still to be sleeved",
    test: TO_BE_SLEEVED,
    hint: "Sleeve them, then tick them off.",
    fix: {
      why: "These games have sleeve requirements that aren't all marked as sleeved yet (🃏 not shown).",
      steps: [
        "To see what to buy: select the games and click Generate Sleeve Shopping List.",
        "Once stock is in, the Sleeve Inventory tab → Ready to Sleeve lists what you can sleeve now. Mark Sleeved ticks the sleeves and deducts the stock.",
        "Or per game: Edit Game → Sleeves tab, and mark each sleeve type as sleeved.",
      ],
    },
  },
  {
    key: "no_image",
    label: "Missing image",
    test: (g) => !g.cloudinary_url && !g.image_url,
    hint: "Re-import from BGG to pull the image.",
    fix: {
      why: "These games show a \"No image\" placeholder on the public site.",
      steps: [
        "Select the games and click Re-import from BGG. It refreshes the image along with the rest of the BGG data.",
        "If it's still missing afterwards, BoardGameGeek has no image for that game, so there's nothing more to do here.",
      ],
    },
  },
  {
    key: "no_designers",
    label: "Missing designers",
    test: (g) => !Array.isArray(g.designers) || g.designers.length === 0,
    hint: "Re-import from BGG to pull designers.",
    fix: {
      why: "Designers are shown on the game page and are used by the NZ designer filter.",
      steps: [
        "Select the games and click Re-import from BGG. Designers come from BoardGameGeek.",
        "If BGG lists none (or only \"Uncredited\") it will stay empty. There's no manual designer field yet.",
      ],
    },
  },
  {
    key: "no_complexity",
    label: "Missing complexity",
    test: (g) => !g.complexity,
    hint: "Re-import from BGG to pull the rating.",
    fix: {
      why: "Complexity is shown on catalogue cards and helps visitors choose a game.",
      steps: [
        "Select the games and click Re-import from BGG.",
        "BGG only publishes a complexity weight once enough people have rated it, so new or obscure games may stay blank until it does.",
      ],
    },
  },
  {
    key: "no_bgg_id",
    label: "No BGG link",
    test: (g) => !g.bgg_id,
    hint: "Re-add via BGG ID, then delete the manual entry.",
    fix: {
      why: "These were added manually, so they can't be refreshed from BoardGameGeek and have no BGG link.",
      steps: [
        "Find the game on boardgamegeek.com and note the number in its URL (the BGG ID).",
        "Open Add Games → Add Game by BGG ID.",
        "Then delete the old manual entry using Delete on its row. Deleting also removes its sleeve data, so fetch sleeves again for the new one.",
      ],
    },
  },
];

export function attentionCounts(games) {
  const counts = {};
  ATTENTION_FILTERS.forEach((f) => {
    counts[f.key] = games.filter(f.test).length;
  });
  return counts;
}
