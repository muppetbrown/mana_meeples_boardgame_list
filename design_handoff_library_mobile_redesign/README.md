# Handoff: Mana & Meeples Game Library — Mobile Redesign

## Overview
Mobile-first redesign of the public board game library catalogue (library.manaandmeeples.co.nz) to match the updated manaandmeeples.co.nz brand. Goals, from café-floor feedback:
- Customers didn't realise the site could *find them a game* — they just scrolled. The new page leads with guided "Who's playing today?" quick-picks and a shelf-of-game-boxes category picker.
- Filters were confusing and stayed open while scrolling. Filters are now a bottom sheet with plain-language questions and a "Show N games" apply button that closes it.
- Aftergame session-planning is promoted: one explainer strip up top + an icon button on every card.
- Search and sort are deliberately removed from the primary UI (customers browse for recommendations; search remains available on the game-details/staff side if needed).

## About the Design Files
The files in this bundle are **design references created in HTML** — a prototype showing intended look and behavior, NOT production code. The task is to **recreate this design in the existing React 19 + Tailwind (v4) frontend** (`frontend/src/`), using its established patterns: React Query data fetching, `useSearchParams` URL state, existing accessibility utilities (LiveRegion, SkipNav, aria-pressed, min 44px targets), and existing API params.

`Library Redesign (Mobile).dc.html` is the deliverable. `Library Current (Mobile).dc.html` is a recreation of today's UI, included only for before/after comparison. Both are self-contained: open in a browser; the phone-width column (max-width 414px) is the design — the grey gutter around it is not part of the page.

## Fidelity
**High-fidelity.** Colors, type, spacing, radii and copy are final unless noted. Recreate pixel-perfectly with Tailwind utilities / CSS.

## Target files in the codebase
- `frontend/src/pages/PublicCatalogue.jsx` — page restructure (hero, quick-picks, shelves, sticky bar, list). Remove: SearchBox from primary UI, SortSelect, desktop filter card (desktop can reuse the mobile layout centered at 414–480px until a desktop pass is done).
- `frontend/src/components/public/GameCardPublic.jsx` + `game-card/GameCardStats.jsx` — replaced by the new card (see below).
- `frontend/src/utils/categoryStyles.js` — new category palette (below).
- New component: `FilterSheet` (bottom sheet) and `ShelfPicker` (game-box category toggles).
- `frontend/src/constants/categories.js` — unchanged keys/labels; display ORDER is now: KIDS_FAMILIES, PARTY_ICEBREAKERS, GATEWAY_STRATEGY, COOP_ADVENTURE, CORE_STRATEGY.
- `index.css` — fonts + cream body background.

## Design Tokens
Fonts (Google Fonts):
- Headings/wordmark/box labels: 'Bricolage Grotesque' 700/800
- Body/UI: 'Source Sans 3' 400/600/700; base 16px, line-height 1.5

Colors:
- Cream page bg `#f7f5ed`; card/sheet bg `white` / `#fdfcf8`
- Ink `#3e473d`; secondary text `#5f726c`; muted `#8a9a85`
- Forest `#3d5135` (primary buttons, headings, active pills); deep teal `#2d4a47` (header gradient end)
- Terracotta `#a35040` (accent: filter-count badge, clear links, quick-pick active border)
- Sage tints: `#e8f0e4` (chips, pressed), `#f2f6ef`, `#fbfaf4`; borders `#d4e0d1`, hairline `#f0f2e8`
- Header gradient: `linear-gradient(170deg, #3d5135 0%, #2d4a47 100%)`, header text white, subtitle `#e8f0e4`, link accents `#cfe0c8`
- Aftergame tint: strip bg `#eef1fd`, border `#d3daf7`
- Shelf wood rail: `linear-gradient(#c9b285, #a8905f)`
- Category colors (categoryStyles.js replacement — solid bg, white text):
  - KIDS_FAMILIES `#7d4a66` · PARTY_ICEBREAKERS `#a06e2c` · GATEWAY_STRATEGY `#3d5135` · COOP_ADVENTURE `#a35040` · CORE_STRATEGY `#2d4a47`

Shape & spacing: cards/tiles radius 14–16px; all buttons/chips are pills (999px); page gutter 20px; card list gap 12px; min tap target 44px.

## Screens / Views — single mobile page, top to bottom

### 1. Header (forest gradient band, padding 16 20 24)
- Row: logo (38px, white circle bg, links to manaandmeeples.co.nz) + "The Game Library" (Bricolage 22px/800, white) + right-aligned "← main site" (13px/600 `#cfe0c8`).
- Subtitle: "{total} games on our shelves — let's find yours." (15px `#e8f0e4`). **Total comes from the live category-counts endpoint** (`counts.all`), not hard-coded.

### 2. Quick-picks ("Who's playing today?")
- H2 Bricolage 19px/700 forest; helper "Tap one and we'll shortlist the shelf for you." 14px `#5f726c`.
- 2×2 grid, gap 10. Each card: white, radius 14, shadow `0 2px 8px rgba(61,81,53,0.08)`, padding 11 13, left-aligned; first line = emoji 17px + label (Bricolage 15px/700) inline; sub-line 12px/600 `#8a9a85`.
- Active state: 2px `#a35040` border, bg `#fdf0ec`, sub-line turns terracotta. Tap toggles on/off (aria-pressed).
- Definitions (trait filters that STACK with shelves and sheet filters):
  - 🎲 First timers — "Learn in minutes, any shelf" → complexity < 2.2
  - 🪸 With the kids — "Simple rules, family fun" → category KIDS_FAMILIES OR complexity < 1.5
  - 🎉 Big group — "Plays well with 5+" → players_max ≥ 5
  - 🤝 Team up — "Win (or lose) together" → cooperative games (prefer BGG `is_cooperative` over category)
  - API mapping: `complexity_max`, `players`, `is_cooperative` (may need a small backend addition for the co-op flag as a filter).

### 3. Shelf picker ("Or browse the shelves")
- H2 17px + helper "Tap a box to take it off the shelf — mix as many as you like." (13px `#8a9a85`).
- Two wooden shelf rails (7px tall, wood gradient, radius 3, shadow `0 3px 4px rgba(61,81,53,0.18)`); boxes sit flush on top, 6px side inset, gap 8.
- Row 1 (3 boxes): Kids & Families, Party & Icebreakers, Gateway Strategy. Row 2 (2 boxes): Co-op & Adventure, Core Strategy & Epics.
- Box = button, flex:1, min-height 64, category color bg, white text, radius `9px 9px 3px 3px`, padding 10 10 8, left-aligned: label (Bricolage 13px/700) over "{count} games" (11px/600, 85% opacity). Count from category-counts endpoint.
- Resting: inset bottom shadow `inset 0 -5px 0 rgba(0,0,0,0.18)` (box-lid depth). Selected: `translateY(-7px)`, shadow `0 10px 16px rgba(61,81,53,0.35)`, inner white ring `inset 0 0 0 2px rgba(255,255,255,0.85)`, and a 20px white ✓ badge (category-color glyph) at top-right (-7, -5). Transition 0.18s transform/box-shadow (respect prefers-reduced-motion).
- Multi-select toggles; **none selected = all games** (no "All" button anywhere).

### 4. Sticky bar (sticks to top on scroll)
- Bg `rgba(247,245,237,0.95)` + `backdrop-filter: blur(12px)`, bottom border `#d4e0d1`.
- One full-width pill button, forest bg, min-height 50: filter-lines icon + "Narrow it down" (15px/700 white) + "players · time · rules" (13px/600 `#cfe0c8`) + right-aligned terracotta count badge (20px circle) when filters active. Opens the bottom sheet.
- When any filter active, a second row of removable chips (sage bg `#e8f0e4`, forest text, "Label ✕", 13px/600) + terracotta "Clear all" text button. Chips: one per quick-pick, per selected shelf, per sheet setting. Row scrolls horizontally if needed.

### 5. Aftergame strip (first item in the list area)
- Bg `#eef1fd`, border `#d3daf7`, radius 14, padding 12 14; Aftergame icon 30px + copy 13px:
  **"Keen to play but short on players? Tap [icon] on any game to organise a session for a day that suits you — and invite anyone in the Mana & Meeples community to join."** ([icon] = inline 15px Aftergame logo.)

### 6. Game cards (vertical list, gap 12)
- Card: white, radius 16, border `#d4e0d1`, shadow `0 2px 8px rgba(61,81,53,0.06)`.
- Main row (padding 12, gap 12): cover 104×104 radius 12 (Cloudinary image; prototype shows striped placeholder) · info column · action column.
- Info: title Bricolage 17px/700; category pill under it (11px/700 white on category color, padding 3 10); then three labelled rows 13px (label 58px `#8a9a85`/600, value forest/700):
  - Players {min–max} · Time {min–max} min · Rules {Easy|Light|Medium|Deep}
  - Rules buckets from BGG complexity: <1.5 Easy · 1.5–2.2 Light · 2.2–3 Medium · ≥3 Deep (same labels in the filter sheet).
- Action column (right edge, space-between): round 44px Aftergame button (white bg, `#d3daf7` border, 24px icon, aria-label "Organise a session on Aftergame", links to `getAfterGameCreateUrl(game.aftergame_game_id)`) above a round 44px chevron expand button (white bg, `#d4e0d1` border; expanded: sage bg, chevron rotated 180°, 0.25s).
- Expanded panel (border-top `#e8f0e4`, padding 14 16 16): description 14px `#5f726c`; 2-col meta grid 14px (Designer / BGG rating "★ x.x / 10" / Complexity "x.x / 5 · {bucket}" / Published); "View full details →" link (14px/700 forest) → `/game/{id}`. One card expanded at a time.

### 7. List footer / empty state
- Footer: "Keep scrolling — {N of total} games on this shelf" 13px `#8a9a85`, centered. Keep existing infinite scroll.
- Empty: "No games match — yet. Try loosening a filter." + terracotta pill "Clear all filters".

### 8. Filter bottom sheet
- Backdrop `rgba(45,58,45,0.5)` (tap closes). Sheet: bottom-anchored, max-width 414 centered, bg `#fdfcf8`, radius 22 22 0 0, shadow `0 -8px 30px rgba(20,30,20,0.25)`, max-height 82vh scroll, padding 18 20 26, sections gap 18. Focus-trap + aria-modal per existing modal patterns.
- Title "Narrow it down" (Bricolage 21px/800) + 44px round ✕ (sage bg).
- Three option groups, each a 14px/700 question + wrapping pill buttons (min-width 52, centered; active = forest bg/white, inactive = white with `#d4e0d1` border). **No "Any" buttons: tap toggles on/off; none = any.** Single-select per group.
  - "How many players?" → 1 2 3 4 5 6+ (API `players`; 6+ → players_max ≥ 6)
  - "How long have you got?" → Under 30 min · 30–60 min · Over an hour (playtime_max buckets)
  - "How much rules-crunch?" + helper "Easy = learn in 5 minutes · Deep = a proper rules session" → Easy · Light · Medium · Deep (API `complexity_min/max` per buckets above)
- Footer row: terracotta "Clear" text button + flex-1 forest pill (min-height 54) "Show {N} game(s)" — live count; when 0: "No matches — loosen up". Tapping closes the sheet (this is the fix for "filters stay open while scrolling").

## State Management
- Filter state in URL params (existing pattern): quickPick, cats[] (multi), players, time, weight; expandedId + sheetOpen are local state.
- All filters combine with AND; games query via React Query with mapped API params. Sort: fixed `title_asc` for now (sort UI removed).
- Counts (`total`, per-category) from `getPublicCategoryCounts` / query totals — nothing hard-coded.
- Keep LiveRegion announcements on filter changes and `aria-pressed` on all toggles.

## Assets
- `assets/logo192.png` — Mana & Meeples logo (already `frontend/public/logo192.png`)
- `assets/aftergame_icon.webp` — Aftergame icon (already `frontend/public/Aftergame_Icon_Logo_V3-Light.webp`)
- Game covers: existing `cloudinary_url`/`image_url` pipeline (prototype uses striped placeholders).
- Fonts: Google Fonts — Bricolage Grotesque (600–800), Source Sans 3 (400–700).

## Files in this bundle
- `Library Redesign (Mobile).dc.html` — the design (open in a browser; interactive: quick-picks, shelf boxes, sheet, expand all work)
- `Library Current (Mobile).dc.html` — recreation of the current UI for comparison
- `assets/` — logo + Aftergame icon
- `screenshots/` — reference captures: `01-redesign.png` (top of page), `02-redesign.png` (filter sheet open), `03-redesign.png` (after sheet close), `cards.png` (game cards)

## Out of scope (unchanged for now)
Desktop-specific layout, game details page, staff/admin views, search UI (removed from this page on purpose), sort UI, dark mode.
