import React from "react";
import GameImage from "../GameImage";
import { labelFor } from "../../constants/categories";

export default function LibraryCard({ game, onEditCategory, onDelete }) {
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
          <div className="font-semibold">{game.title}</div>
          <div className="text-sm text-gray-600">
            {game.min_players ?? "?"}–{game.max_players ?? "?"} · {game.playing_time ?? "?"} mins
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {game.mana_meeple_category ? labelFor(game.mana_meeple_category) : "Uncategorized"}
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
