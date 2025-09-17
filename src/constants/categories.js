// Enum KEYS as sent by the backend in mana_meeple_category
export const CATEGORY_KEYS = [
  "COOP_ADVENTURE",
  "CORE_STRATEGY",
  "GATEWAY_STRATEGY",
  "KIDS_FAMILIES",
  "PARTY_ICEBREAKERS",
];

// Human labels for UI
export const CATEGORY_LABELS = {
  COOP_ADVENTURE: "Co-op & Adventure",
  CORE_STRATEGY: "Core Strategy & Epics",
  GATEWAY_STRATEGY: "Gateway Strategy",
  KIDS_FAMILIES: "Kids & Families",
  PARTY_ICEBREAKERS: "Party & Icebreakers",
};

export const labelFor = (key) => CATEGORY_LABELS[key] ?? key ?? "—";

// Back-compat aliases for any older imports (can delete later)
export const GAME_CATEGORIES = CATEGORY_KEYS;
export const getCategoryDisplayName = labelFor;
