// src/components/staff/ManualGameEntryPanel.jsx
import React, { useState } from "react";
import { addGame } from "../../api/client";
import { CATEGORY_KEYS, CATEGORY_LABELS } from "../../constants/categories";

/**
 * Manual game entry panel - for adding games when BGG API is down
 * Supports copy-paste from BoardGameGeek with proper data type validation
 */
export function ManualGameEntryPanel({ onSuccess, onToast }) {
  const [formData, setFormData] = useState({
    title: "",
    bgg_id: "",
    year: "",
    players_min: "",
    players_max: "",
    playtime_min: "",
    playtime_max: "",
    min_age: "",
    description: "",
    designers: "",
    publishers: "",
    mechanics: "",
    artists: "",
    thumbnail_url: "",
    image: "",
    average_rating: "",
    complexity: "",
    bgg_rank: "",
    users_rated: "",
    is_cooperative: false,
    nz_designer: false,
    mana_meeple_category: "",
    game_type: "",
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCheckbox = (field) => {
    setFormData((prev) => ({ ...prev, [field]: !prev[field] }));
  };

  const clearForm = () => {
    setFormData({
      title: "",
      bgg_id: "",
      year: "",
      players_min: "",
      players_max: "",
      playtime_min: "",
      playtime_max: "",
      min_age: "",
      description: "",
      designers: "",
      publishers: "",
      mechanics: "",
      artists: "",
      thumbnail_url: "",
      image: "",
      average_rating: "",
      complexity: "",
      bgg_rank: "",
      users_rated: "",
      is_cooperative: false,
      nz_designer: false,
      mana_meeple_category: "",
      game_type: "",
    });
  };

  const parseJsonArray = (value) => {
    if (!value || !value.trim()) return null;
    // Split by comma, trim each item, filter out empty strings
    return value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  };

  const parseInteger = (value) => {
    if (!value || !value.trim()) return null;
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? null : parsed;
  };

  const parseFloatValue = (value) => {
    if (!value || !value.trim()) return null;
    const parsed = Number.parseFloat(value);
    return isNaN(parsed) ? null : parsed;
  };

  const validateAndPrepare = () => {
    // Title is required
    if (!formData.title.trim()) {
      onToast("Title is required", "error");
      return null;
    }

    const payload = {
      title: formData.title.trim(),
    };

    // Optional fields with type conversion
    if (formData.bgg_id) payload.bgg_id = parseInteger(formData.bgg_id);
    if (formData.year) payload.year = parseInteger(formData.year);
    if (formData.players_min) payload.players_min = parseInteger(formData.players_min);
    if (formData.players_max) payload.players_max = parseInteger(formData.players_max);
    if (formData.playtime_min) payload.playtime_min = parseInteger(formData.playtime_min);
    if (formData.playtime_max) payload.playtime_max = parseInteger(formData.playtime_max);
    if (formData.min_age) payload.min_age = parseInteger(formData.min_age);
    if (formData.bgg_rank) payload.bgg_rank = parseInteger(formData.bgg_rank);
    if (formData.users_rated) payload.users_rated = parseInteger(formData.users_rated);

    if (formData.average_rating) payload.average_rating = parseFloatValue(formData.average_rating);
    if (formData.complexity) payload.complexity = parseFloatValue(formData.complexity);

    // Text fields
    if (formData.description) payload.description = formData.description.trim();
    if (formData.thumbnail_url) payload.thumbnail_url = formData.thumbnail_url.trim();
    if (formData.image) payload.image = formData.image.trim();
    if (formData.mana_meeple_category) payload.mana_meeple_category = formData.mana_meeple_category;
    if (formData.game_type) payload.game_type = formData.game_type.trim();

    // Boolean fields
    payload.is_cooperative = formData.is_cooperative;
    payload.nz_designer = formData.nz_designer;

    // JSON array fields (comma-separated input)
    const designers = parseJsonArray(formData.designers);
    if (designers) payload.designers = designers;

    const publishers = parseJsonArray(formData.publishers);
    if (publishers) payload.publishers = publishers;

    const mechanics = parseJsonArray(formData.mechanics);
    if (mechanics) payload.mechanics = mechanics;

    const artists = parseJsonArray(formData.artists);
    if (artists) payload.artists = artists;

    return payload;
  };

  const handleSubmit = async () => {
    const payload = validateAndPrepare();
    if (!payload) return;

    setIsSubmitting(true);
    try {
      const result = await addGame(payload);
      onToast(`Game "${result.title || formData.title}" added successfully!`, "success");
      clearForm();
      if (onSuccess) onSuccess(result);
    } catch (error) {
      console.error("Failed to add game:", error);
      onToast(
        error.response?.data?.detail || "Failed to add game. Check console for details.",
        "error"
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 shadow space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Manual Game Entry</h3>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-purple-600 hover:text-purple-700"
        >
          {showAdvanced ? "Hide" : "Show"} Advanced Fields
        </button>
      </div>

      <p className="text-sm text-gray-600">
        Add games manually by copying data from BoardGameGeek. Fields marked with * are required.
      </p>

      {/* Basic Information */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-700">Basic Information</h4>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title *
          </label>
          <input
            type="text"
            className="w-full border rounded-lg px-3 py-2"
            placeholder="e.g., Pandemic"
            value={formData.title}
            onChange={(e) => handleChange("title", e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              BGG ID
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 30549"
              value={formData.bgg_id}
              onChange={(e) => handleChange("bgg_id", e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Year Published
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 2008"
              value={formData.year}
              onChange={(e) => handleChange("year", e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Min Players
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 2"
              value={formData.players_min}
              onChange={(e) => handleChange("players_min", e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Players
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 4"
              value={formData.players_max}
              onChange={(e) => handleChange("players_max", e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Min Playtime (minutes)
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 45"
              value={formData.playtime_min}
              onChange={(e) => handleChange("playtime_min", e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Playtime (minutes)
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., 60"
              value={formData.playtime_max}
              onChange={(e) => handleChange("playtime_max", e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Minimum Age
          </label>
          <input
            type="text"
            className="w-full border rounded-lg px-3 py-2"
            placeholder="e.g., 8"
            value={formData.min_age}
            onChange={(e) => handleChange("min_age", e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Designers (comma-separated)
          </label>
          <input
            type="text"
            className="w-full border rounded-lg px-3 py-2"
            placeholder="e.g., Matt Leacock"
            value={formData.designers}
            onChange={(e) => handleChange("designers", e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-1">
            Separate multiple designers with commas
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            className="w-full border rounded-lg px-3 py-2 h-24"
            placeholder="Game description..."
            value={formData.description}
            onChange={(e) => handleChange("description", e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            className="w-full border rounded-lg px-3 py-2"
            value={formData.mana_meeple_category}
            onChange={(e) => handleChange("mana_meeple_category", e.target.value)}
          >
            <option value="">-- Select Category --</option>
            {CATEGORY_KEYS.map((key) => (
              <option key={key} value={key}>
                {CATEGORY_LABELS[key]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.is_cooperative}
              onChange={() => handleCheckbox("is_cooperative")}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Cooperative Game</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={formData.nz_designer}
              onChange={() => handleCheckbox("nz_designer")}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">NZ Designer</span>
          </label>
        </div>
      </div>

      {/* Advanced Fields */}
      {showAdvanced && (
        <div className="space-y-3 pt-4 border-t">
          <h4 className="font-medium text-gray-700">Advanced Fields</h4>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Thumbnail URL
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="https://..."
                value={formData.thumbnail_url}
                onChange={(e) => handleChange("thumbnail_url", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Full Image URL
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="https://..."
                value={formData.image}
                onChange={(e) => handleChange("image", e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Publishers (comma-separated)
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., Z-Man Games, Filosofia"
              value={formData.publishers}
              onChange={(e) => handleChange("publishers", e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Mechanics (comma-separated)
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., Cooperative Game, Hand Management, Set Collection"
              value={formData.mechanics}
              onChange={(e) => handleChange("mechanics", e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Artists (comma-separated)
            </label>
            <input
              type="text"
              className="w-full border rounded-lg px-3 py-2"
              placeholder="e.g., Josh Cappel, Chris Quilliams"
              value={formData.artists}
              onChange={(e) => handleChange("artists", e.target.value)}
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                BGG Rating
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2"
                placeholder="e.g., 7.6"
                value={formData.average_rating}
                onChange={(e) => handleChange("average_rating", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Complexity (1-5)
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2"
                placeholder="e.g., 2.4"
                value={formData.complexity}
                onChange={(e) => handleChange("complexity", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                BGG Rank
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2"
                placeholder="e.g., 50"
                value={formData.bgg_rank}
                onChange={(e) => handleChange("bgg_rank", e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Users Rated
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2"
                placeholder="e.g., 45000"
                value={formData.users_rated}
                onChange={(e) => handleChange("users_rated", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Game Type
              </label>
              <input
                type="text"
                className="w-full border rounded-lg px-3 py-2"
                placeholder="e.g., Board Game"
                value={formData.game_type}
                onChange={(e) => handleChange("game_type", e.target.value)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 pt-4">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || !formData.title.trim()}
          className={`px-6 py-2 rounded-lg text-white font-medium ${
            isSubmitting || !formData.title.trim()
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-purple-600 hover:bg-purple-700"
          }`}
        >
          {isSubmitting ? "Adding Game..." : "Add Game"}
        </button>

        <button
          onClick={clearForm}
          disabled={isSubmitting}
          className="px-6 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
        >
          Clear Form
        </button>
      </div>
    </div>
  );
}
