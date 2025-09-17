import React from "react";
import GameImage from "../GameImage";
import { CATEGORY_KEYS, labelFor } from "../../constants/categories";

export default function SearchBGGPanel({
  searchQuery,
  setSearchQuery,
  isSearching,
  results,
  onSearch,
  onAddToLibrary,
}) {
  return (
    <section className="bg-white rounded-2xl p-6 shadow">
      <h2 className="text-xl font-semibold mb-3">Search BoardGameGeek</h2>
      <div className="flex flex-wrap gap-2 items-center">
        <input
          className="flex-1 min-w-[240px] border rounded-lg px-3 py-2"
          placeholder="Search title…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
        />
        <button
          className="px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
          onClick={onSearch}
          disabled={isSearching}
        >
          {isSearching ? "Searching…" : "Search"}
        </button>
      </div>

      {results?.length > 0 && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((game) => (
            <div key={game.bgg_id} className="group bg-white border rounded-xl p-4 hover:shadow-lg transition">
              <div className="flex gap-4">
                <GameImage
                  url={game.image_url}
                  alt={game.title}
                  className="w-20 h-20 object-cover rounded-xl border-2 border-gray-200 group-hover:border-purple-300 transition-all duration-300 shadow"
                  fallbackClass="w-20 h-20 bg-gray-200 rounded-xl flex items-center justify-center text-gray-500 text-sm border-2 border-gray-200"
                />
                <div className="flex-1">
                  <div className="font-semibold">{game.title}</div>
                  <div className="text-sm text-gray-600">
                    {game.min_players ?? "?"}–{game.max_players ?? "?"} · {game.playing_time ?? "?"} mins
                  </div>
                  <div className="mt-2 flex gap-2 flex-wrap">
                    {CATEGORY_KEYS.map((c) => (
                      <button
                        key={c}
                        className="text-xs px-2 py-1 rounded border hover:bg-purple-50"
                        onClick={() => onAddToLibrary(game, c)}
                      >
                        Add to {labelFor(c)}
                      </button>
                    ))}
                    <button
                      className="text-xs px-2 py-1 rounded border bg-gray-50 hover:bg-gray-100"
                      onClick={() => onAddToLibrary(game, null)}
                      title="Choose category…"
                    >
                      Choose Category…
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
