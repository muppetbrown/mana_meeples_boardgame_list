import { describe, test, expect } from 'vitest';
import { classifySleeve, groupItems, SLEEVE_GROUPS, OTHER_GROUP, groupSizeLabel } from '../sleeveGroups';

const sz = (w, h, name) => classifySleeve({ name, width_mm: w, height_mm: h }).key;

describe('classifySleeve by size', () => {
  test.each([
    [41, 63, 'mini_american'],
    [45, 68, 'mini_european'],
    [56, 87, 'standard_american'],
    [59, 92, 'standard_european'],
    [63.5, 88, 'standard_card'],
    [73, 73, 'square'],
    [70, 120, 'tarot'],
  ])('%s x %s -> %s', (w, h, key) => {
    expect(sz(w, h)).toBe(key);
  });

  test('inner sleeve sizes with normal slack still land in their group', () => {
    expect(sz(57, 89)).toBe('standard_american'); // +1 wide, +2 tall
    expect(sz(46, 71)).toBe('mini_european');
    expect(sz(42, 66)).toBe('mini_american');
  });

  test('numeric strings (API decimals) are accepted', () => {
    expect(sz('56.00', '87.00')).toBe('standard_american');
  });

  test('unrecognised sizes fall into Other', () => {
    expect(classifySleeve({ width_mm: 100, height_mm: 100 })).toBe(OTHER_GROUP);
    expect(classifySleeve({ width_mm: undefined, height_mm: null })).toBe(OTHER_GROUP);
  });

  test('an exact tie between overlapping groups goes to the earlier one', () => {
    // 57.5 x 89.5 is equally far from Standard American (56x87) and Standard European (59x92)
    expect(sz(57.5, 89.5)).toBe('standard_american');
  });

  test('picks the nearest group when windows overlap', () => {
    expect(sz(59, 92)).toBe('standard_european');
    expect(sz(56, 88)).toBe('standard_american');
  });
});

describe('classifySleeve by name', () => {
  test('a group keyword in the name beats the size', () => {
    expect(sz(59, 92, 'Ultimate Guard Standard American sleeves')).toBe('standard_american');
    expect(sz(100, 100, 'Dragon Shield Mini European')).toBe('mini_european');
    expect(sz(1, 1, 'Mini US 41x63')).toBe('mini_american');
    expect(sz(1, 1, 'Standard Euro Premium')).toBe('standard_european');
  });

  test('mini names are not mistaken for standard ones', () => {
    expect(sz(59, 92, 'Mini American')).toBe('mini_american');
  });

  test('"mini square" is not classed as Square', () => {
    expect(sz(100, 100, 'Mini Square')).toBe('other');
    expect(sz(100, 100, 'Square 73x73')).toBe('square');
  });

  test('falls back to size when the name has no keyword', () => {
    expect(sz(45, 68, 'Generic sleeves 100pk')).toBe('mini_european');
  });
});

describe('groupItems', () => {
  const items = [
    { id: 1, width_mm: 59, height_mm: 92 },
    { id: 2, width_mm: 41, height_mm: 63 },
    { id: 3, width_mm: 100, height_mm: 100 },
    { id: 4, width_mm: 41, height_mm: 63 },
  ];

  test('orders groups canonically with Other last and omits empty groups', () => {
    const grouped = groupItems(items, (i) => i);
    expect(grouped.map((g) => g.group.key)).toEqual(['mini_american', 'standard_european', 'other']);
    expect(grouped[0].items.map((i) => i.id)).toEqual([2, 4]);
  });

  test('empty input gives no groups', () => {
    expect(groupItems([], (i) => i)).toEqual([]);
  });

  test('size label formatting', () => {
    expect(groupSizeLabel(SLEEVE_GROUPS[0])).toBe('41 × 63 mm');
    expect(groupSizeLabel(OTHER_GROUP)).toBe('');
  });
});
