import { describe, test, expect } from 'vitest';
import { ATTENTION_FILTERS, attentionCounts, SLEEVE_UNKNOWN } from '../libraryQuality';

const good = {
  id: 1, mana_meeple_category: 'CORE_STRATEGY', has_sleeves: 'found',
  image_url: 'x', designers: ['A'], complexity: 2, bgg_id: 5,
};

describe('libraryQuality', () => {
  test('a complete game triggers no checks', () => {
    expect(attentionCounts([good])).toEqual({
      uncategorized: 0, sleeves_unknown: 0, no_image: 0, no_designers: 0, no_complexity: 0, no_bgg_id: 0,
    });
  });

  test.each([
    ['uncategorized', { mana_meeple_category: null }],
    ['sleeves_unknown', { has_sleeves: null }],
    ['sleeves_unknown', { has_sleeves: 'not_found' }],
    ['sleeves_unknown', { has_sleeves: 'check' }],
    ['sleeves_unknown', { has_sleeves: 'error' }],
    ['no_image', { image_url: null }],
    ['no_designers', { designers: [] }],
    ['no_designers', { designers: null }],
    ['no_complexity', { complexity: 0 }],
    ['no_bgg_id', { bgg_id: null }],
  ])('%s flags %j', (key, patch) => {
    const f = ATTENTION_FILTERS.find((x) => x.key === key);
    expect(f.test({ ...good, ...patch })).toBe(true);
  });

  test("'none' and 'manual' sleeve statuses are considered resolved", () => {
    expect(SLEEVE_UNKNOWN({ ...good, has_sleeves: 'none' })).toBe(false);
    expect(SLEEVE_UNKNOWN({ ...good, has_sleeves: 'manual' })).toBe(false);
  });

  test('a cloudinary url counts as having an image', () => {
    const f = ATTENTION_FILTERS.find((x) => x.key === 'no_image');
    expect(f.test({ ...good, image_url: null, cloudinary_url: 'c' })).toBe(false);
  });
});
