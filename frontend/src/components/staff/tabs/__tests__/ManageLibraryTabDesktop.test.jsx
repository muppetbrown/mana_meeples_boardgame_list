/**
 * ManageLibraryTab desktop workflow features: sortable headers, density,
 * page/cross-page selection, shift-click range select, rows per page, empty state.
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageLibraryTab } from '../ManageLibraryTab';

vi.mock('../../../../api/client', () => ({
  generateSleeveShoppingList: vi.fn(),
  triggerSleeveFetch: vi.fn(),
  generateGameLabels: vi.fn(),
  reimportSelectedGames: vi.fn(),
  imageProxyUrl: (u) => u,
  getSleeveFetchStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
}));
vi.mock('../../../../context/StaffContext', () => ({ useStaff: vi.fn() }));
vi.mock('../../../CategoryFilter', () => ({ default: () => <div /> }));
vi.mock('../../GameEditModal', () => ({ default: () => <div /> }));
vi.mock('../../SleeveShoppingListModal', () => ({ default: () => <div /> }));
vi.mock('../../SleeveFetchStatus', () => ({ default: () => null }));

import { useStaff } from '../../../../context/StaffContext';

const make = (n) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    title: `Game ${String(i + 1).padStart(3, '0')}`,
    year: 2000 + (i % 20),
    bgg_id: 1000 + i,
    mana_meeple_category: 'CORE_STRATEGY',
    designers: [],
    players_min: 2,
    players_max: 4,
    playtime_min: 30,
    playtime_max: 60,
    complexity: 2.5,
    average_rating: 7.234,
    date_added: `2025-01-01T00:${String(i % 60).padStart(2, '0')}:00Z`,
  }));

const ctx = (list, over = {}) => ({
  selectedCategory: 'all', setSelectedCategory: vi.fn(), counts: {}, filteredLibrary: list, library: list,
  deleteGameData: vi.fn(), updateGameData: vi.fn(), showToast: vi.fn(), loadLibrary: vi.fn(),
  confirm: vi.fn().mockResolvedValue(true), attentionFilter: '', setAttentionFilter: vi.fn(),
  isLoading: false, ...over,
});

const rowTitles = () =>
  screen.getAllByRole('row').slice(1).map((r) => within(r).getByText(/^(Game \d+)$/).textContent);

describe('ManageLibraryTab desktop features', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  test('shows players, time, weight and rating columns', () => {
    useStaff.mockReturnValue(ctx(make(2)));
    render(<ManageLibraryTab />);
    expect(screen.getByText('Players')).toBeInTheDocument();
    expect(screen.getAllByText('2–4').length).toBe(2);
    expect(screen.getAllByText('30–60m').length).toBe(2);
    expect(screen.getAllByText('2.5').length).toBe(2);
    expect(screen.getAllByText('7.2').length).toBe(2);
  });

  test('clicking the Name header sorts A-Z, clicking again reverses', async () => {
    const user = userEvent.setup();
    useStaff.mockReturnValue(ctx(make(3)));
    render(<ManageLibraryTab />);
    const header = screen.getByRole('columnheader', { name: /Name/ });
    expect(header).toHaveAttribute('aria-sort', 'none');
    await user.click(within(header).getByRole('button'));
    expect(rowTitles()).toEqual(['Game 001', 'Game 002', 'Game 003']);
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute('aria-sort', 'ascending');
    await user.click(within(screen.getByRole('columnheader', { name: /Name/ })).getByRole('button'));
    expect(rowTitles()).toEqual(['Game 003', 'Game 002', 'Game 001']);
    expect(screen.getByRole('columnheader', { name: /Name/ })).toHaveAttribute('aria-sort', 'descending');
  });

  test('density defaults to compact and persists the choice', async () => {
    const user = userEvent.setup();
    useStaff.mockReturnValue(ctx(make(2)));
    render(<ManageLibraryTab />);
    expect(screen.getByRole('button', { name: 'Compact' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: 'Comfortable' }));
    expect(screen.getByRole('button', { name: 'Comfortable' })).toHaveAttribute('aria-pressed', 'true');
    expect(localStorage.getItem('staff.library.density')).toBe('comfortable');
  });

  test('select-all covers the page and offers to select every matching game', async () => {
    const user = userEvent.setup();
    useStaff.mockReturnValue(ctx(make(120)));
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select page (50)'));
    expect(screen.getByText('50 game(s) selected')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Select all 120 matching games' }));
    expect(screen.getByText('120 game(s) selected')).toBeInTheDocument();
    expect(screen.getByText(/All/, { selector: 'div[role="status"]' })).toHaveTextContent('120 matching games are selected');
    await user.click(screen.getByRole('button', { name: 'Clear selection' }));
    expect(screen.getByText('0 game(s) selected')).toBeInTheDocument();
  });

  test('shift-click selects a range of rows', async () => {
    const user = userEvent.setup();
    useStaff.mockReturnValue(ctx(make(10)));
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select Game 002'));
    await user.keyboard('{Shift>}');
    await user.click(screen.getByLabelText('Select Game 005'));
    await user.keyboard('{/Shift}');
    expect(screen.getByText('4 game(s) selected')).toBeInTheDocument();
    expect(screen.getByLabelText('Select Game 004')).toBeChecked();
    expect(screen.getByLabelText('Select Game 006')).not.toBeChecked();
  });

  test('rows-per-page selector changes the page size', async () => {
    const user = userEvent.setup();
    useStaff.mockReturnValue(ctx(make(120)));
    render(<ManageLibraryTab />);
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Rows per page'), '100');
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument();
  });

  test('empty state offers to clear active filters', async () => {
    const user = userEvent.setup();
    const setAttentionFilter = vi.fn();
    const setSelectedCategory = vi.fn();
    useStaff.mockReturnValue(ctx(make(3), { setAttentionFilter, setSelectedCategory }));
    render(<ManageLibraryTab />);
    await user.type(screen.getByLabelText('Search library'), 'zzz-nothing');
    await user.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(screen.getByLabelText('Search library')).toHaveValue('');
    expect(setAttentionFilter).toHaveBeenCalledWith('');
    expect(setSelectedCategory).toHaveBeenCalledWith('all');
  });

  test('shows skeleton rows while the first load is in flight', () => {
    useStaff.mockReturnValue(ctx([], { isLoading: true }));
    render(<ManageLibraryTab />);
    expect(screen.getByRole('status', { name: 'Loading library' })).toBeInTheDocument();
  });

  test('quality filter can isolate games missing an AfterGame ID', () => {
    const list = make(3);
    list[0].aftergame_game_id = 'ac3a5f77-3e19-47af-a61a-d648d04b02e2';
    useStaff.mockReturnValue(ctx(list, { attentionFilter: 'no_aftergame' }));
    render(<ManageLibraryTab />);
    expect(screen.getByRole('option', { name: 'Needs attention: Missing AfterGame ID' })).toBeInTheDocument();
    expect(rowTitles()).toEqual(['Game 003', 'Game 002']);
  });
});
