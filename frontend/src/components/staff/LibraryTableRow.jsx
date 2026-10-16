// src/components/staff/LibraryTableRow.jsx
import React from "react";
import Thumbnail from "../common/Thumbnail";
import Icon from "../common/Icon";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../../constants/categories";

const range = (min, max, suffix = "") => {
  if (!min && !max) return "—";
  if (!max || min === max) return `${min || max}${suffix}`;
  if (!min) return `${max}${suffix}`;
  return `${min}–${max}${suffix}`;
};

function SleeveBadge({ game }) {
  if (game.fully_sleeved) {
    return (
      <span title="All sleeve requirements marked as sleeved" className="text-sm leading-none">
        🃏
      </span>
    );
  }
  if (game.has_sleeves === "none") {
    return (
      <span title="No sleeve requirements for this game" className="text-xs leading-none">
        🚫🃏
      </span>
    );
  }
  if (game.has_sleeves === "not_found" || game.has_sleeves === "check" || !game.has_sleeves) {
    return (
      <span title="Sleeve status needs investigation" className="text-xs leading-none">
        ❓🃏
      </span>
    );
  }
  return null;
}

/**
 * One row of the Manage Library table. Memoised: with 50+ rows, toggling one
 * checkbox should only re-render that row, so all callbacks passed in must be stable.
 */
function LibraryTableRowImpl({ game, index, selected, saving, compact, onToggle, onCategoryChange, onEdit, onDelete }) {
  const cell = compact ? "px-3 py-1" : "px-3 py-2.5";
  const standalone = game.expansion_type === "both" || game.expansion_type === "standalone";

  return (
    <tr className={`transition-colors ${selected ? "bg-purple-50/60" : "hover:bg-gray-50"}`}>
      <td className={`${cell} whitespace-nowrap text-center w-10`}>
        <input
          type="checkbox"
          aria-label={`Select ${game.title}`}
          checked={selected}
          onChange={(e) => onToggle(game.id, index, e.nativeEvent.shiftKey)}
          className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 cursor-pointer"
        />
      </td>

      <td className={`${cell} whitespace-nowrap w-12`}>
        <Thumbnail
          src={game.cloudinary_url || game.image_url}
          alt={game.title}
          size={compact ? "w-8 h-8" : "w-12 h-12"}
        />
      </td>

      <td className={`${cell} min-w-0`}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900">{game.title}</span>
          <SleeveBadge game={game} />
          {compact && game.year && <span className="text-xs text-gray-500 tabular">{game.year}</span>}
        </div>
        {!compact && game.year && <div className="text-xs text-gray-500">{game.year}</div>}
      </td>

      <td className={`${cell} whitespace-nowrap`}>
        {game.is_expansion ? (
          <div className="flex flex-col gap-0.5">
            <span
              className={`inline-flex w-fit px-2 py-0.5 text-[11px] font-semibold rounded-full ${
                standalone ? "bg-indigo-100 text-indigo-800" : "bg-purple-100 text-purple-800"
              }`}
            >
              {standalone ? "STANDALONE" : "EXPANSION"}
            </span>
            {game.modifies_players_max && (
              <span className="text-xs text-purple-600">
                +{game.modifies_players_min ?? game.players_min}-{game.modifies_players_max}p
              </span>
            )}
          </div>
        ) : (
          <span className="inline-flex px-2 py-0.5 text-[11px] font-medium rounded-full bg-gray-100 text-gray-600">
            Base Game
          </span>
        )}
      </td>

      <td className={`${cell} whitespace-nowrap text-sm text-gray-700 tabular hidden xl:table-cell`}>
        {range(game.players_min, game.players_max)}
      </td>
      <td className={`${cell} whitespace-nowrap text-sm text-gray-700 tabular hidden xl:table-cell`}>
        {range(game.playtime_min, game.playtime_max, "m")}
      </td>
      <td className={`${cell} whitespace-nowrap text-sm text-gray-700 tabular text-right hidden xl:table-cell`}>
        {game.complexity ? Number(game.complexity).toFixed(1) : "—"}
      </td>
      <td className={`${cell} whitespace-nowrap text-sm text-gray-700 tabular text-right hidden xl:table-cell`}>
        {game.average_rating ? Number(game.average_rating).toFixed(1) : "—"}
      </td>

      <td className={cell}>
        <select
          aria-label={`Category for ${game.title}`}
          value={game.mana_meeple_category || ""}
          disabled={saving}
          onChange={(e) => onCategoryChange(game, e.target.value)}
          className={`text-xs font-medium rounded-md border px-2 py-1 outline-none focus:ring-2 focus:ring-purple-300 disabled:opacity-50 ${
            game.mana_meeple_category
              ? "bg-purple-50 text-purple-800 border-purple-200"
              : "bg-gray-100 text-gray-600 border-gray-300"
          }`}
        >
          <option value="">Uncategorized</option>
          {CATEGORY_KEYS.map((key) => (
            <option key={key} value={key}>
              {CATEGORY_LABELS[key]}
            </option>
          ))}
        </select>
      </td>

      <td className={`${cell} whitespace-nowrap text-right`}>
        <div className="flex items-center justify-end gap-1">
          <button
            onClick={() => onEdit(game)}
            className="inline-flex items-center gap-1.5 h-7 px-2.5 text-xs font-medium rounded-md border border-gray-300 bg-white text-gray-700 hover:bg-purple-50 hover:border-purple-300 hover:text-purple-700 transition-colors"
            title="View game info and edit details"
            aria-label={`Info and edit: ${game.title}`}
          >
            <Icon name="edit" size={13} />
            Edit
          </button>
          <button
            onClick={() => onDelete(game)}
            aria-label={`Delete ${game.title}`}
            title="Delete game"
            className="inline-flex items-center justify-center h-7 w-7 rounded-md text-gray-400 hover:text-red-700 hover:bg-red-50 transition-colors"
          >
            <Icon name="trash" size={14} />
          </button>
        </div>
      </td>
    </tr>
  );
}

export const LibraryTableRow = React.memo(LibraryTableRowImpl);
export default LibraryTableRow;
