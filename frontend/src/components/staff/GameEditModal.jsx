// src/components/staff/GameEditModal.jsx
import React, { useState, useEffect } from 'react';
import { CATEGORY_KEYS, CATEGORY_LABELS } from '../../constants/categories';
import SleevesListTable from './SleevesListTable';
import Modal from '../common/Modal';

const STATUS_OPTIONS = [
  { value: 'OWNED', label: 'Owned' },
  { value: 'BUY_LIST', label: 'Buy list' },
  { value: 'WISHLIST', label: 'Wishlist' },
];

const inputCls =
  'w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-900 outline-none transition focus:border-purple-500 focus:ring-2 focus:ring-purple-200';

const toInt = (v) => {
  if (v === '' || v === null || v === undefined) return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
};

const isValidUUID = (str) =>
  !str || /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);

function Section({ title, hint, children }) {
  return (
    <section className="px-5 py-4">
      <div className="mb-2.5 flex items-baseline justify-between gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
        {hint && <span className="text-xs text-gray-400">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

function Field({ label, htmlFor, children, className = '' }) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-gray-600">
        {label}
      </label>
      {children}
    </div>
  );
}

/** Accessible on/off switch rendered as a checkbox (role="checkbox" keeps semantics simple). */
function Switch({ id, checked, onChange, label, description }) {
  return (
    <label
      htmlFor={id}
      className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 transition ${
        checked ? 'border-purple-300 bg-purple-50' : 'border-gray-200 hover:bg-gray-50'
      }`}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className={`relative h-5 w-9 shrink-0 rounded-full transition peer-focus-visible:ring-2 peer-focus-visible:ring-purple-400 peer-focus-visible:ring-offset-1 ${
          checked ? 'bg-purple-600' : 'bg-gray-300'
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
            checked ? 'left-[18px]' : 'left-0.5'
          }`}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-gray-900">{label}</span>
        {description && <span className="block text-xs text-gray-500">{description}</span>}
      </span>
    </label>
  );
}

/**
 * Unified modal for editing a game: core details, category, flags (NZ designer,
 * ownership status), expansion info, sleeves and AfterGame link, as one compact
 * scrollable form with a pinned footer.
 */
export default function GameEditModal({ game, library, onSave, onClose, onSleeveUpdate }) {
  const [validationErrors, setValidationErrors] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    year: '',
    players_min: '',
    players_max: '',
    playtime_min: '',
    playtime_max: '',
    min_age: '',
    mana_meeple_category: null,
    nz_designer: false,
    status: 'OWNED',
    is_expansion: false,
    expansion_type: 'requires_base',
    base_game_id: null,
    modifies_players_min: null,
    modifies_players_max: null,
    aftergame_game_id: null,
  });

  useEffect(() => {
    if (game) {
      setFormData({
        title: game.title || '',
        year: game.year ?? '',
        players_min: game.players_min ?? '',
        players_max: game.players_max ?? '',
        playtime_min: game.playtime_min ?? '',
        playtime_max: game.playtime_max ?? '',
        min_age: game.min_age ?? '',
        mana_meeple_category: game.mana_meeple_category || null,
        nz_designer: !!game.nz_designer,
        status: game.status || 'OWNED',
        is_expansion: game.is_expansion || false,
        expansion_type: game.expansion_type || 'requires_base',
        base_game_id: game.base_game_id || null,
        modifies_players_min: game.modifies_players_min || null,
        modifies_players_max: game.modifies_players_max || null,
        aftergame_game_id: game.aftergame_game_id || null,
      });
    }
  }, [game]);

  if (!game) return null;

  const possibleBaseGames = library.filter((g) => g.id !== game.id && !g.is_expansion);

  const handleChange = (field, value) => setFormData((prev) => ({ ...prev, [field]: value }));
  const numberProps = (field, extra = {}) => ({
    type: 'number',
    inputMode: 'numeric',
    value: formData[field] ?? '',
    onChange: (e) => handleChange(field, e.target.value),
    className: inputCls,
    ...extra,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const errors = [];

    if (!formData.title.trim()) errors.push('Title is required');

    const range = (label, min, max, lo, hi) => {
      const a = toInt(min);
      const b = toInt(max);
      if (a !== null && (a < lo || a > hi)) errors.push(`${label} min must be between ${lo} and ${hi}`);
      if (b !== null && (b < lo || b > hi)) errors.push(`${label} max must be between ${lo} and ${hi}`);
      if (a !== null && b !== null && a > b) errors.push(`${label} min cannot be greater than max`);
    };
    range('Players', formData.players_min, formData.players_max, 1, 99);
    range('Playtime', formData.playtime_min, formData.playtime_max, 1, 1440);

    if (formData.is_expansion) {
      const minP = toInt(formData.modifies_players_min);
      const maxP = toInt(formData.modifies_players_max);
      if (minP !== null && (minP < 1 || minP > 99)) errors.push('Min players must be between 1 and 99');
      if (maxP !== null && (maxP < 1 || maxP > 99)) errors.push('Max players must be between 1 and 99');
      if (minP !== null && maxP !== null && minP > maxP) {
        errors.push('Min players cannot be greater than max players');
      }
    }

    const year = toInt(formData.year);
    if (year !== null && (year < 1800 || year > 2100)) errors.push('Year looks wrong (expected 1800–2100)');

    if (formData.aftergame_game_id && !isValidUUID(formData.aftergame_game_id)) {
      errors.push('AfterGame ID must be a valid UUID format (e.g., ac3a5f77-3e19-47af-a61a-d648d04b02e2)');
    }

    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }
    setValidationErrors([]);

    const saveData = {
      title: formData.title.trim(),
      year,
      players_min: toInt(formData.players_min),
      players_max: toInt(formData.players_max),
      playtime_min: toInt(formData.playtime_min),
      playtime_max: toInt(formData.playtime_max),
      min_age: toInt(formData.min_age),
      mana_meeple_category: formData.mana_meeple_category || null,
      nz_designer: formData.nz_designer,
      status: formData.status,
      is_expansion: formData.is_expansion,
      expansion_type: formData.is_expansion ? formData.expansion_type : null,
      base_game_id: formData.is_expansion && formData.base_game_id ? parseInt(formData.base_game_id, 10) : null,
      modifies_players_min: toInt(formData.modifies_players_min),
      modifies_players_max: toInt(formData.modifies_players_max),
      aftergame_game_id: formData.aftergame_game_id || null,
    };

    setIsSaving(true);
    Promise.resolve(onSave(saveData)).finally(() => setIsSaving(false));
  };

  const thumb = game.thumbnail_url || game.image_url;

  return (
    <Modal onClose={onClose} labelledBy="edit-game-title" maxWidth="max-w-2xl">
      <form onSubmit={handleSubmit} className="flex max-h-[90vh] flex-col">
        {/* Header */}
        <header className="flex items-center gap-3 border-b border-gray-200 bg-gray-50 px-5 py-3 rounded-t-2xl">
          {thumb ? (
            <img src={thumb} alt="" className="h-12 w-12 shrink-0 rounded-md bg-gray-200 object-cover" />
          ) : (
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-gray-200 text-lg" aria-hidden="true">
              🎲
            </div>
          )}
          <div className="min-w-0 flex-1">
            <h2 id="edit-game-title" className="text-xs font-medium uppercase tracking-wide text-purple-600">Edit Game</h2>
            <p className="truncate text-base font-semibold text-gray-900" title={game.title}>{game.title}</p>
            <p className="truncate text-xs text-gray-500">
              <span className="font-mono">ID {game.id}</span>
              {game.bgg_id ? (
                <>
                  {' · BGG '}
                  <a
                    href={`https://boardgamegeek.com/boardgame/${game.bgg_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-purple-600 underline hover:text-purple-800"
                  >
                    {game.bgg_id}
                  </a>
                </>
              ) : null}
              {game.designers?.length ? ` · ${game.designers.join(', ')}` : ''}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-200 hover:text-gray-700"
          >
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </header>

        {/* Scrollable body */}
        <div className="min-h-0 flex-1 divide-y divide-gray-100 overflow-y-auto">
          <Section title="Details">
            <div className="grid grid-cols-6 gap-x-3 gap-y-3">
              <Field label="Title" htmlFor="edit-title" className="col-span-6 sm:col-span-4">
                <input
                  id="edit-title"
                  type="text"
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  className={inputCls}
                />
              </Field>
              <Field label="Year" htmlFor="edit-year" className="col-span-3 sm:col-span-1">
                <input id="edit-year" {...numberProps('year')} />
              </Field>
              <Field label="Min age" htmlFor="edit-min-age" className="col-span-3 sm:col-span-1">
                <input id="edit-min-age" {...numberProps('min_age')} />
              </Field>
              <div className="col-span-6 grid grid-cols-2 gap-3 sm:col-span-3">
                <Field label="Players min" htmlFor="edit-players-min">
                  <input id="edit-players-min" {...numberProps('players_min')} />
                </Field>
                <Field label="Players max" htmlFor="edit-players-max">
                  <input id="edit-players-max" {...numberProps('players_max')} />
                </Field>
              </div>
              <div className="col-span-6 grid grid-cols-2 gap-3 sm:col-span-3">
                <Field label="Time min (mins)" htmlFor="edit-time-min">
                  <input id="edit-time-min" {...numberProps('playtime_min')} />
                </Field>
                <Field label="Time max (mins)" htmlFor="edit-time-max">
                  <input id="edit-time-max" {...numberProps('playtime_max')} />
                </Field>
              </div>
            </div>
          </Section>

          <Section title="Category" hint="Shown as a filter in the public catalogue">
            <div role="radiogroup" aria-label="Category" className="flex flex-wrap gap-2">
              {[...CATEGORY_KEYS, null].map((key) => {
                const selected = formData.mana_meeple_category === key;
                const label = key ? CATEGORY_LABELS[key] : 'Uncategorized';
                return (
                  <label
                    key={key ?? 'none'}
                    className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm font-medium transition focus-within:ring-2 focus-within:ring-purple-400 ${
                      selected
                        ? key
                          ? 'border-purple-600 bg-purple-600 text-white'
                          : 'border-gray-600 bg-gray-600 text-white'
                        : 'border-gray-300 bg-white text-gray-700 hover:border-purple-300 hover:bg-purple-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="category"
                      value={key ?? ''}
                      checked={selected}
                      onChange={() => handleChange('mana_meeple_category', key)}
                      className="sr-only"
                    />
                    {label}
                  </label>
                );
              })}
            </div>
          </Section>

          <Section title="Flags">
            <div className="grid gap-3 sm:grid-cols-2">
              <Switch
                id="nz_designer"
                checked={formData.nz_designer}
                onChange={(v) => handleChange('nz_designer', v)}
                label="New Zealand designer 🇳🇿"
                description="Highlighted in the NZ filter"
              />
              <Field label="Ownership status" htmlFor="edit-status">
                <select
                  id="edit-status"
                  value={formData.status}
                  onChange={(e) => handleChange('status', e.target.value)}
                  className={inputCls}
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </Field>
            </div>
          </Section>

          <Section title="Expansion">
            <Switch
              id="is_expansion"
              checked={formData.is_expansion}
              onChange={(v) => handleChange('is_expansion', v)}
              label="This is an expansion"
            />
            {formData.is_expansion && (
              <div className="mt-3 grid gap-3 border-l-2 border-purple-300 pl-3 sm:grid-cols-2">
                <Field label="Expansion Type" htmlFor="expansion_type">
                  <select
                    id="expansion_type"
                    value={formData.expansion_type}
                    onChange={(e) => handleChange('expansion_type', e.target.value)}
                    className={inputCls}
                  >
                    <option value="requires_base">Requires Base Game</option>
                    <option value="standalone">Standalone (can be played alone)</option>
                    <option value="both">Both (standalone OR with base game)</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    {formData.expansion_type === 'requires_base'
                      ? '🔒 Will NOT appear in public catalogue'
                      : '✅ Will appear in public catalogue'}
                  </p>
                </Field>
                <Field label="Base Game (Optional)" htmlFor="base_game_id">
                  <select
                    id="base_game_id"
                    value={formData.base_game_id || ''}
                    onChange={(e) => handleChange('base_game_id', e.target.value || null)}
                    className={inputCls}
                  >
                    <option value="">-- None --</option>
                    {possibleBaseGames.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.title} {g.year ? `(${g.year})` : ''}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="sm:col-span-2">
                  <span className="mb-1 block text-xs font-medium text-gray-600">
                    Modified Player Count (Optional)
                  </span>
                  <div className="flex items-center gap-2">
                    <input
                      aria-label="Modified player count minimum"
                      placeholder="Min"
                      min="1"
                      max="99"
                      {...numberProps('modifies_players_min')}
                      className={`${inputCls} max-w-[6rem]`}
                    />
                    <span className="text-sm text-gray-400">to</span>
                    <input
                      aria-label="Modified player count maximum"
                      placeholder="Max"
                      min="1"
                      max="99"
                      {...numberProps('modifies_players_max')}
                      className={`${inputCls} max-w-[6rem]`}
                    />
                    <span className="text-xs text-gray-500">e.g. a "5-6 Player Extension"</span>
                  </div>
                </div>
              </div>
            )}
          </Section>

          <Section title="Sleeves" hint="Unmarked sleeve types go on the shopping list">
            <SleevesListTable
              gameId={game.id}
              hasSleeves={game.has_sleeves}
              onSleeveUpdate={onSleeveUpdate}
            />
            <p className="mt-2 text-xs text-gray-500">
              <strong>Note:</strong> Mark individual sleeve types as sleeved above. The shopping list will only
              include unmarked sleeve types.
            </p>
          </Section>

          <Section title="AfterGame">
            <Field label="AfterGame Game ID" htmlFor="aftergame_game_id">
              <input
                type="text"
                id="aftergame_game_id"
                value={formData.aftergame_game_id || ''}
                onChange={(e) => handleChange('aftergame_game_id', e.target.value.trim() || null)}
                placeholder="e.g., ac3a5f77-3e19-47af-a61a-d648d04b02e2"
                className={`${inputCls} font-mono text-xs`}
              />
            </Field>
            <p className="mt-1.5 text-xs text-gray-500">
              AfterGame Integration: lets visitors plan a session straight from the library. UUID from AfterGame's URL.
            </p>
            <p
              className={`mt-2 rounded-md px-2.5 py-1.5 text-xs ${
                formData.aftergame_game_id ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'
              }`}
            >
              {formData.aftergame_game_id
                ? '✅ When set, the "Plan a Game" button will link directly to this specific game on AfterGame'
                : 'ℹ️ Without an AfterGame ID, the "Plan a Game" button will link to the generic game creation page'}
            </p>
          </Section>
        </div>

        {/* Footer */}
        <footer className="rounded-b-2xl border-t border-gray-200 bg-white px-5 py-3">
          {validationErrors.length > 0 && (
            <div role="alert" className="mb-3 rounded-md border border-red-200 bg-red-50 px-3 py-2">
              <p className="text-xs font-semibold text-red-800">Please fix the following errors:</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-red-700">
                {validationErrors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-purple-700 disabled:opacity-60"
            >
              {isSaving ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </footer>
      </form>
    </Modal>
  );
}
