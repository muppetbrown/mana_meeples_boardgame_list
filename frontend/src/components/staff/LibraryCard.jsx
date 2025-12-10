import React from "react";
import GameImage from "../GameImage";
import { labelFor } from "../../constants/categories";

export default function LibraryCard({ game, onEditCategory, onDelete }) {
  // Check if this looks like an expansion based on title or fields
  const isExpansion = game.is_expansion ||
    game.title?.toLowerCase().includes('expansion') ||
    game.title?.toLowerCase().includes('extension');

  const expansionType = game.expansion_type || 'requires_base';

  // Debug: Log the game data to console
  console.log('LibraryCard game data:', {
    title: game.title,
    is_expansion: game.is_expansion,
    expansion_type: game.expansion_type,
    base_game_id: game.base_game_id,
    isExpansion: isExpansion,
    allKeys: Object.keys(game)
  });

  return (
    <div className="group bg-white border rounded-xl p-4 hover:shadow-md transition">
      <div className="flex gap-6">
        <GameImage
          url={game.image_url}
          alt={game.title}
          className="w-20 h-20 object-cover rounded-xl border-2 border-gray-200 group-hover:border-purple-300 transition-all duration-300 shadow"
          fallbackClass="w-20 h-20 bg-gradient-to-br from-gray-200 to-gray-300 rounded-xl flex items-center justify-center text-gray-500 text-sm border-2 border-gray-200"
        />
        <div className="flex-1">
          {/* VISIBLE DEBUG INFO */}
          <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs font-mono">
            <div>is_expansion: {JSON.stringify(game.is_expansion)}</div>
            <div>expansion_type: {JSON.stringify(game.expansion_type)}</div>
            <div>base_game_id: {JSON.stringify(game.base_game_id)}</div>
            <div>isExpansion calc: {JSON.stringify(isExpansion)}</div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div className="font-semibold">{game.title}</div>
            {/* Expansion badges */}
            {isExpansion && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                expansionType === 'both' || expansionType === 'standalone'
                  ? 'bg-indigo-100 text-indigo-800'
                  : 'bg-purple-100 text-purple-800'
              }`}>
                {expansionType === 'both' || expansionType === 'standalone'
                  ? 'STANDALONE'
                  : 'EXPANSION'}
              </span>
            )}
            {/* Show raw is_expansion status for debugging */}
            {game.is_expansion !== undefined && (
              <span className="text-xs text-gray-400">
                [is_expansion: {String(game.is_expansion)}]
              </span>
            )}
          </div>
          <div className="text-sm text-gray-600">
            {game.min_players ?? "?"}–{game.max_players ?? "?"} · {game.playing_time ?? "?"} mins
            {game.is_expansion && game.modifies_players_max && (
              <span className="text-purple-600 ml-1 font-medium">
                (extends to {game.modifies_players_min ?? game.min_players}-{game.modifies_players_max})
              </span>
            )}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {game.mana_meeple_category ? labelFor(game.mana_meeple_category) : "Uncategorized"}
            {game.is_expansion && game.base_game_id && (
              <span className="ml-2 text-purple-600">• Expansion</span>
            )}
          </div>

          <div className="mt-3 flex gap-2">
            <button
              className="text-xs px-2 py-1 rounded border hover:bg-purple-50"
              onClick={() => onEditCategory(game)}
            >
              Edit Category
            </button>
            <button
              className="text-xs px-2 py-1 rounded border bg-red-50 hover:bg-red-100"
              onClick={() => onDelete(game)}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
