/**
 * ManageLibraryTab extras - sorting, quality filter, selection, bulk actions
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageLibraryTab } from '../ManageLibraryTab';
import * as apiClient from '../../../../api/client';

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
vi.mock('../../SleeveShoppingListModal', () => ({
  default: ({ onClose }) => (
    <div data-testid="shopping-modal"><button onClick={onClose}>Close list</button></div>
  ),
}));
vi.mock('../../SleeveFetchStatus', () => ({ default: () => null }));

import { useStaff } from '../../../../context/StaffContext';

const games = [
  { id: 1, title: 'Beta', year: 2010, bgg_id: 11, mana_meeple_category: 'CORE_STRATEGY', designers: ['Zed'], date_added: '2025-01-01T00:00:00Z', complexity: 2, image_url: 'x' },
  { id: 2, title: 'Alpha', year: 2020, bgg_id: 22, mana_meeple_category: null, designers: ['Amy'], date_added: '2025-02-01T00:00:00Z', complexity: null, image_url: null },
  { id: 3, title: 'Gamma', year: 2015, bgg_id: 33, mana_meeple_category: 'COOP_ADVENTURE', designers: [], date_added: '2025-03-01T00:00:00Z', complexity: 3, image_url: 'x' },
];

describe('ManageLibraryTab extras', () => {
  const confirm = vi.fn();
  const setAttentionFilter = vi.fn();
  const showToast = vi.fn();
  const ctx = (over = {}) => ({
    selectedCategory: 'all', setSelectedCategory: vi.fn(), counts: {}, filteredLibrary: games, library: games,
    deleteGameData: vi.fn(), updateGameData: vi.fn(), showToast, loadLibrary: vi.fn(),
    confirm, attentionFilter: '', setAttentionFilter, ...over,
  });
  const titles = () => screen.getAllByText(/^(Alpha|Beta|Gamma)$/).map((n) => n.textContent);

  beforeEach(() => {
    vi.clearAllMocks();
    confirm.mockResolvedValue(true);
    useStaff.mockReturnValue(ctx());
  });

  test('sorts by title, year and category', async () => {
    const user = userEvent.setup();
    render(<ManageLibraryTab />);
    expect(titles()).toEqual(['Gamma', 'Alpha', 'Beta']); // newest added first
    await user.selectOptions(screen.getByLabelText('Sort library'), 'title');
    expect(titles()).toEqual(['Alpha', 'Beta', 'Gamma']);
    await user.selectOptions(screen.getByLabelText('Sort library'), 'year');
    expect(titles()).toEqual(['Alpha', 'Gamma', 'Beta']);
    await user.selectOptions(screen.getByLabelText('Sort library'), 'category');
    expect(titles()).toEqual(['Gamma', 'Beta', 'Alpha']); // uncategorised last
  });

  test('searches by designer and BGG id', async () => {
    const user = userEvent.setup();
    render(<ManageLibraryTab />);
    await user.type(screen.getByLabelText('Search library'), 'amy');
    expect(titles()).toEqual(['Alpha']);
    await user.clear(screen.getByLabelText('Search library'));
    await user.type(screen.getByLabelText('Search library'), '33');
    expect(titles()).toEqual(['Gamma']);
  });

  test('quality filter dropdown updates context and applies the filter', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ManageLibraryTab />);
    await user.selectOptions(screen.getByLabelText('Data quality filter'), 'no_image');
    expect(setAttentionFilter).toHaveBeenCalledWith('no_image');
    useStaff.mockReturnValue(ctx({ attentionFilter: 'no_image' }));
    rerender(<ManageLibraryTab />);
    expect(titles()).toEqual(['Alpha']);
  });

  test('select all / clear selection', async () => {
    const user = userEvent.setup();
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText(/Select All 3|Deselect All/));
    expect(screen.getByText('3 game(s) selected')).toBeInTheDocument();
    await user.click(screen.getByText('Clear'));
    expect(screen.getByText('0 game(s) selected')).toBeInTheDocument();
  });

  test('re-import selected asks for confirmation then calls the API', async () => {
    const user = userEvent.setup();
    apiClient.reimportSelectedGames.mockResolvedValue({ message: 'Started' });
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select Beta'));
    await user.click(screen.getByText(/Re-import from BGG/));
    await waitFor(() => expect(apiClient.reimportSelectedGames).toHaveBeenCalledWith([1]));
    expect(showToast).toHaveBeenCalledWith('Started', 'success');
    expect(screen.getByText('0 game(s) selected')).toBeInTheDocument();
  });

  test('re-import is skipped when the confirmation is declined', async () => {
    const user = userEvent.setup();
    confirm.mockResolvedValue(false);
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select Beta'));
    await user.click(screen.getByText(/Re-import from BGG/));
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(apiClient.reimportSelectedGames).not.toHaveBeenCalled();
  });

  test('re-import failure surfaces the server detail', async () => {
    const user = userEvent.setup();
    apiClient.reimportSelectedGames.mockRejectedValue({ response: { data: { detail: 'BGG down' } } });
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select Beta'));
    await user.click(screen.getByText(/Re-import from BGG/));
    await waitFor(() => expect(showToast).toHaveBeenCalledWith('BGG down', 'error'));
  });

  test('shopping list modal opens and closes', async () => {
    const user = userEvent.setup();
    apiClient.generateSleeveShoppingList.mockResolvedValue([{ width_mm: 1 }]);
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Select Beta'));
    await user.click(screen.getByText(/Generate Sleeve Shopping List/));
    expect(await screen.findByTestId('shopping-modal')).toBeInTheDocument();
    await user.click(screen.getByText('Close list'));
    expect(screen.queryByTestId('shopping-modal')).not.toBeInTheDocument();
  });

  test('bulk actions with nothing selected are disabled', () => {
    render(<ManageLibraryTab />);
    expect(screen.getByText(/Print Labels/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Fetch Sleeve Data/).closest('button')).toBeDisabled();
  });

  test('a failed inline category change does not throw', async () => {
    const user = userEvent.setup();
    const updateGameData = vi.fn().mockRejectedValue(new Error('x'));
    useStaff.mockReturnValue(ctx({ updateGameData }));
    render(<ManageLibraryTab />);
    await user.selectOptions(screen.getByLabelText('Category for Alpha'), 'CORE_STRATEGY');
    await waitFor(() => expect(updateGameData).toHaveBeenCalledWith(2, { mana_meeple_category: 'CORE_STRATEGY' }));
    // select is re-enabled afterwards
    await waitFor(() => expect(screen.getByLabelText('Category for Alpha')).not.toBeDisabled());
  });

  test('choosing the same category is a no-op; choosing Uncategorized sends null', async () => {
    const user = userEvent.setup();
    const updateGameData = vi.fn().mockResolvedValue({});
    useStaff.mockReturnValue(ctx({ updateGameData }));
    render(<ManageLibraryTab />);
    await user.selectOptions(screen.getByLabelText('Category for Beta'), 'CORE_STRATEGY');
    expect(updateGameData).not.toHaveBeenCalled();
    await user.selectOptions(screen.getByLabelText('Category for Beta'), '');
    expect(updateGameData).toHaveBeenCalledWith(1, { mana_meeple_category: null });
  });

  test('declining the delete confirmation keeps the game', async () => {
    const user = userEvent.setup();
    confirm.mockResolvedValue(false);
    const deleteGameData = vi.fn();
    useStaff.mockReturnValue(ctx({ deleteGameData }));
    render(<ManageLibraryTab />);
    await user.click(screen.getByLabelText('Delete Beta'));
    expect(deleteGameData).not.toHaveBeenCalled();
  });
});
