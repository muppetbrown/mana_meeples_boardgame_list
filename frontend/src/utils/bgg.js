// src/utils/bgg.js

/**
 * Parse a BoardGameGeek ID from either a bare number or a pasted BGG URL
 * (e.g. https://boardgamegeek.com/boardgame/30549/pandemic or
 * .../boardgameexpansion/342 942/...). Returns a positive integer, or null
 * if nothing valid could be found.
 */
export function parseBggId(raw) {
  const input = (raw || "").trim();
  if (!input) return null;
  const urlMatch = input.match(/boardgame(?:expansion)?\/(\d+)/i);
  const id = parseInt(urlMatch ? urlMatch[1] : input, 10);
  return Number.isInteger(id) && id > 0 ? id : null;
}
