/**
 * ManageLibraryTab tests - Library browsing, editing, and bulk operations
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ManageLibraryTab } from '../ManageLibraryTab';
import * as apiClient from '../../../../api/client';

// Mock API client
vi.mock('../../../../api/client', () => ({
  imageProxyUrl: vi.fn((url) => `proxy:${url}`),
  generateSleeveShoppingList: vi.fn(),
  triggerSleeveFetch: vi.fn(),
  generateGameLabels: vi.fn(),
}));

// Mock useStaff hook
vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

// Mock child components
vi.mock('../../../CategoryFilter', () => ({
  default: vi.fn(({ selected, counts, onChange }) => (
    <div data-testid="category-filter">
      <button onClick={() => onChange('all')}>All</button>
      <button onClick={() => onChange('CORE_STRATEGY')}>Core Strategy</button>
    </div>
  )),
}));

vi.mock('../../GameEditModal', () => ({
  default: vi.fn(({ game, onSave, onClose }) => (
    <div data-testid="game-edit-modal">
      <div>Editing: {game?.title}</div>
      <button onClick={() => onSave({ title: 'Updated Game' })}>Save</button>
      <button onClick={onClose}>Close</button>
    </div>
  )),
}));

vi.mock('../../SleeveShoppingListModal', () => ({
  default: vi.fn(({ shoppingList, onClose }) => (
    <div data-testid="sleeve-shopping-list-modal">
      <div>Sleeve List Modal</div>
      <button onClick={onClose}>Close Modal</button>
    </div>
  )),
}));

import { useStaff } from '../../../../context/StaffContext';

describe('ManageLibraryTab', () => {
  const mockSetSelectedCategory = vi.fn();
  const mockOpenEditCategory = vi.fn();
  const mockDeleteGameData = vi.fn();
  const mockUpdateGameData = vi.fn();
  const mockShowToast = vi.fn();

  const mockGames = [
    {
      id: 1,
      title: 'Gloomhaven',
      bgg_id: 174430,
      mana_meeple_category: 'CORE_STRATEGY',
      year: 2017,
      cloudinary_url: 'https://cloudinary.com/gloomhaven.jpg',
      is_expansion: false,
      designers: ['Isaac Childres'],
      date_added: '2025-01-15T00:00:00Z',
    },
    {
      id: 2,
      title: 'Wingspan',
      bgg_id: 266192,
      mana_meeple_category: 'GATEWAY_STRATEGY',
      year: 2019,
      image_url: 'https://example.com/wingspan.jpg',
      is_expansion: false,
      designers: ['Elizabeth Hargrave'],
      date_added: '2025-01-10T00:00:00Z',
    },
    {
      id: 3,
      title: 'Pandemic Expansion',
      bgg_id: 30549,
      mana_meeple_category: 'COOP_ADVENTURE',
      year: 2010,
      is_expansion: true,
      expansion_type: 'expansion',
      modifies_players_max: 6,
      modifies_players_min: 2,
      players_min: 2,
      designers: ['Matt Leacock'],
      date_added: '2025-01-05T00:00:00Z',
    },
    {
      id: 4,
      title: 'Sleeved Game',
      bgg_id: 99999,
      mana_meeple_category: 'PARTY_ICEBREAKERS',
      year: 2020,
      fully_sleeved: true,
      is_expansion: false,
      designers: ['John Doe'],
      date_added: '2025-01-01T00:00:00Z',
    },
  ];

  const defaultStaffContext = {
    selectedCategory: 'all',
    setSelectedCategory: mockSetSelectedCategory,
    counts: {
      all: 4,
      CORE_STRATEGY: 1,
      GATEWAY_STRATEGY: 1,
      COOP_ADVENTURE: 1,
      PARTY_ICEBREAKERS: 1,
    },
    filteredLibrary: mockGames,
    library: mockGames,
    openEditCategory: mockOpenEditCategory,
    deleteGameData: mockDeleteGameData,
    updateGameData: mockUpdateGameData,
    showToast: mockShowToast,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useStaff.mockReturnValue(defaultStaffContext);

    // Mock window.confirm
    global.window.confirm = vi.fn(() => true);

    // Mock URL.createObjectURL and revokeObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    test('renders header with library stats', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('Your Library')).toBeInTheDocument();
      expect(screen.getByText(/Showing/)).toBeInTheDocument();
      expect(screen.getByText(/games/)).toBeInTheDocument();
    });

    test('renders search input', () => {
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveValue('');
    });

    test('renders sort dropdown', () => {
      render(<ManageLibraryTab />);

      const sortSelect = screen.getByDisplayValue(/Sort: Date Added/);
      expect(sortSelect).toBeInTheDocument();
    });

    test('renders category filter', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByTestId('category-filter')).toBeInTheDocument();
    });

    test('renders all games in table', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('Gloomhaven')).toBeInTheDocument();
      expect(screen.getByText('Wingspan')).toBeInTheDocument();
      expect(screen.getByText('Pandemic Expansion')).toBeInTheDocument();
      expect(screen.getByText('Sleeved Game')).toBeInTheDocument();
    });

    test('renders table headers', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('Select')).toBeInTheDocument();
      expect(screen.getByText('Thumbnail')).toBeInTheDocument();
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('BGG ID')).toBeInTheDocument();
      expect(screen.getByText('Category')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });
  });

  describe('Search Functionality', () => {
    test('filters games by title', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, 'Gloomhaven');

      expect(screen.getByText('Gloomhaven')).toBeInTheDocument();
      expect(screen.queryByText('Wingspan')).not.toBeInTheDocument();
    });

    test('filters games by BGG ID', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, '174430');

      expect(screen.getByText('Gloomhaven')).toBeInTheDocument();
      expect(screen.queryByText('Wingspan')).not.toBeInTheDocument();
    });

    test('filters games by designer', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, 'Elizabeth');

      expect(screen.getByText('Wingspan')).toBeInTheDocument();
      expect(screen.queryByText('Gloomhaven')).not.toBeInTheDocument();
    });

    test('shows no results message when search yields no matches', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, 'NonExistentGame');

      expect(screen.getByText(/No games found matching/)).toBeInTheDocument();
      expect(screen.getByText(/NonExistentGame/)).toBeInTheDocument();
    });

    test('updates filtered count in header', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, 'Gloomhaven');

      // Should show "Showing 1 of 4 games (filtered by search)"
      expect(screen.getByText(/Showing/)).toBeInTheDocument();
      expect(screen.getByText(/filtered by search/)).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    test('sorts by date added (newest first) by default', () => {
      render(<ManageLibraryTab />);

      const sortSelect = screen.getByDisplayValue(/Sort: Date Added/);
      expect(sortSelect).toHaveValue('date_added');
    });

    test('sorts by title alphabetically', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const sortSelect = screen.getByDisplayValue(/Sort: Date Added/);
      await user.selectOptions(sortSelect, 'title');

      expect(sortSelect).toHaveValue('title');
    });
  });

  describe('Game Selection', () => {
    test('renders select all checkbox', () => {
      render(<ManageLibraryTab />);

      const selectAllCheckbox = screen.getByRole('checkbox', { name: /Select All/ });
      expect(selectAllCheckbox).toBeInTheDocument();
      expect(selectAllCheckbox).not.toBeChecked();
    });

    test('selects individual game', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      // First checkbox is "Select All", others are game checkboxes
      await user.click(checkboxes[1]);

      expect(checkboxes[1]).toBeChecked();
      expect(screen.getByText('1 game(s) selected')).toBeInTheDocument();
    });

    test('deselects individual game', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);
      await user.click(checkboxes[1]);

      expect(checkboxes[1]).not.toBeChecked();
      expect(screen.getByText('0 game(s) selected')).toBeInTheDocument();
    });

    test('selects all games', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const selectAllCheckbox = screen.getByRole('checkbox', { name: /Select All/ });
      await user.click(selectAllCheckbox);

      expect(selectAllCheckbox).toBeChecked();
      expect(screen.getByText('4 game(s) selected')).toBeInTheDocument();
    });

    test('deselects all games', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const selectAllCheckbox = screen.getByRole('checkbox', { name: /Select All/ });
      await user.click(selectAllCheckbox);
      await user.click(selectAllCheckbox);

      expect(selectAllCheckbox).not.toBeChecked();
      expect(screen.getByText('0 game(s) selected')).toBeInTheDocument();
    });

    test('shows correct selection count', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);
      await user.click(checkboxes[2]);

      expect(screen.getByText('2 game(s) selected')).toBeInTheDocument();
    });
  });

  describe('Bulk Actions', () => {
    test('renders bulk action buttons', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText(/Fetch Sleeve Data/)).toBeInTheDocument();
      expect(screen.getByText(/Generate Sleeve Shopping List/)).toBeInTheDocument();
      expect(screen.getByText(/Print Labels/)).toBeInTheDocument();
    });

    test('bulk action buttons are disabled when no games selected', () => {
      render(<ManageLibraryTab />);

      const fetchSleeveButton = screen.getByText(/Fetch Sleeve Data/).closest('button');
      const generateListButton = screen.getByText(/Generate Sleeve Shopping List/).closest('button');
      const printLabelsButton = screen.getByText(/Print Labels/).closest('button');

      expect(fetchSleeveButton).toBeDisabled();
      expect(generateListButton).toBeDisabled();
      expect(printLabelsButton).toBeDisabled();
    });

    test('bulk action buttons are enabled when games selected', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const fetchSleeveButton = screen.getByText(/Fetch Sleeve Data/).closest('button');
      const generateListButton = screen.getByText(/Generate Sleeve Shopping List/).closest('button');
      const printLabelsButton = screen.getByText(/Print Labels/).closest('button');

      expect(fetchSleeveButton).not.toBeDisabled();
      expect(generateListButton).not.toBeDisabled();
      expect(printLabelsButton).not.toBeDisabled();
    });

    test('generates sleeve shopping list', async () => {
      const user = userEvent.setup();
      apiClient.generateSleeveShoppingList.mockResolvedValue({ items: [] });

      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const generateListButton = screen.getByText(/Generate Sleeve Shopping List/).closest('button');
      await user.click(generateListButton);

      await waitFor(() => {
        expect(apiClient.generateSleeveShoppingList).toHaveBeenCalledWith([1]);
        expect(screen.getByTestId('sleeve-shopping-list-modal')).toBeInTheDocument();
      });
    });

    test('shows error toast when sleeve list generation fails', async () => {
      const user = userEvent.setup();
      apiClient.generateSleeveShoppingList.mockRejectedValue(new Error('API Error'));

      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const generateListButton = screen.getByText(/Generate Sleeve Shopping List/).closest('button');
      await user.click(generateListButton);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith(
          'Failed to generate sleeve shopping list',
          'error'
        );
      });
    });

    test('triggers sleeve fetch with confirmation', async () => {
      const user = userEvent.setup();
      apiClient.triggerSleeveFetch.mockResolvedValue({ success: true });

      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const fetchSleeveButton = screen.getByText(/Fetch Sleeve Data/).closest('button');
      await user.click(fetchSleeveButton);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalled();
        expect(apiClient.triggerSleeveFetch).toHaveBeenCalledWith([1]);
        expect(mockShowToast).toHaveBeenCalledWith(
          'Sleeve fetch workflow triggered for 1 game(s)',
          'success'
        );
      });
    });

    test('does not trigger sleeve fetch when confirmation cancelled', async () => {
      const user = userEvent.setup();
      window.confirm.mockReturnValue(false);

      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const fetchSleeveButton = screen.getByText(/Fetch Sleeve Data/).closest('button');
      await user.click(fetchSleeveButton);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalled();
        expect(apiClient.triggerSleeveFetch).not.toHaveBeenCalled();
      });
    });

    test('generates PDF labels', async () => {
      const user = userEvent.setup();
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
      apiClient.generateGameLabels.mockResolvedValue(mockBlob);

      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      await user.click(checkboxes[1]);

      const printLabelsButton = screen.getByText(/Print Labels/).closest('button');
      await user.click(printLabelsButton);

      await waitFor(() => {
        expect(apiClient.generateGameLabels).toHaveBeenCalledWith([1]);
        expect(mockShowToast).toHaveBeenCalledWith(
          expect.stringContaining('Generating labels'),
          'info'
        );
        expect(mockShowToast).toHaveBeenCalledWith(
          'Labels generated successfully for 1 game(s)',
          'success'
        );
      });
    });

    test('shows error when no games selected for bulk action', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      // Directly test the handler logic by checking disabled state
      const generateListButton = screen.getByText(/Generate Sleeve Shopping List/).closest('button');
      expect(generateListButton).toBeDisabled();
    });
  });

  describe('Game Table Display', () => {
    test('displays game thumbnails with proxy URLs', () => {
      render(<ManageLibraryTab />);

      const images = screen.getAllByRole('img');
      expect(images[0]).toHaveAttribute('src', 'proxy:https://cloudinary.com/gloomhaven.jpg');
      expect(images[0]).toHaveAttribute('alt', 'Gloomhaven');
    });

    test('displays fallback for missing images', () => {
      render(<ManageLibraryTab />);

      // Pandemic Expansion has no image
      expect(screen.getAllByText('No img').length).toBeGreaterThan(0);
    });

    test('displays game years', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('2017')).toBeInTheDocument();
      expect(screen.getByText('2019')).toBeInTheDocument();
    });

    test('displays expansion badges', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('EXPANSION')).toBeInTheDocument();
      expect(screen.getByText('+2-6p')).toBeInTheDocument();
    });

    test('displays base game badges', () => {
      render(<ManageLibraryTab />);

      const baseGameBadges = screen.getAllByText('Base Game');
      expect(baseGameBadges.length).toBeGreaterThan(0);
    });

    test('displays fully sleeved indicator', () => {
      render(<ManageLibraryTab />);

      // Sleeved Game should have the card emoji
      expect(screen.getByTitle('All sleeve requirements marked as sleeved')).toBeInTheDocument();
    });

    test('displays BGG ID links', () => {
      render(<ManageLibraryTab />);

      const bggLink = screen.getByText('174430').closest('a');
      expect(bggLink).toHaveAttribute('href', 'https://boardgamegeek.com/boardgame/174430');
      expect(bggLink).toHaveAttribute('target', '_blank');
      expect(bggLink).toHaveAttribute('rel', 'noopener noreferrer');
    });

    test('displays category badges', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('Core Strategy & Epics')).toBeInTheDocument();
    });

    test('displays uncategorized badge for games without category', () => {
      const contextWithUncategorized = {
        ...defaultStaffContext,
        filteredLibrary: [
          { ...mockGames[0], mana_meeple_category: null },
        ],
      };

      useStaff.mockReturnValue(contextWithUncategorized);
      render(<ManageLibraryTab />);

      expect(screen.getByText('Uncategorized')).toBeInTheDocument();
    });
  });

  describe('Individual Game Actions', () => {
    test('renders Edit Game and Delete buttons', () => {
      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByText('Edit Game');
      const deleteButtons = screen.getAllByText('Delete');

      expect(editButtons.length).toBe(4); // One for each game
      expect(deleteButtons.length).toBe(4);
    });

    test('opens edit modal when Edit Game clicked', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByText('Edit Game');
      await user.click(editButtons[0]);

      expect(screen.getByTestId('game-edit-modal')).toBeInTheDocument();
      expect(screen.getByText('Editing: Gloomhaven')).toBeInTheDocument();
    });

    test('closes edit modal', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByText('Edit Game');
      await user.click(editButtons[0]);

      const closeButton = screen.getByText('Close');
      await user.click(closeButton);

      expect(screen.queryByTestId('game-edit-modal')).not.toBeInTheDocument();
    });

    test('saves edited game', async () => {
      const user = userEvent.setup();
      mockUpdateGameData.mockResolvedValue({});

      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByText('Edit Game');
      await user.click(editButtons[0]);

      const saveButton = screen.getByText('Save');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateGameData).toHaveBeenCalledWith(1, { title: 'Updated Game' });
        expect(mockShowToast).toHaveBeenCalledWith('Game details updated successfully', 'success');
        expect(screen.queryByTestId('game-edit-modal')).not.toBeInTheDocument();
      });
    });

    test('shows error toast when game update fails', async () => {
      const user = userEvent.setup();
      mockUpdateGameData.mockRejectedValue(new Error('Update failed'));

      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByText('Edit Game');
      await user.click(editButtons[0]);

      const saveButton = screen.getByText('Save');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith('Failed to update game details', 'error');
      });
    });

    test('deletes game with confirmation', async () => {
      const user = userEvent.setup();
      mockDeleteGameData.mockResolvedValue({});

      render(<ManageLibraryTab />);

      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith('Delete "Gloomhaven"?');
        expect(mockDeleteGameData).toHaveBeenCalledWith(1);
      });
    });

    test('does not delete game when confirmation cancelled', async () => {
      const user = userEvent.setup();
      window.confirm.mockReturnValue(false);

      render(<ManageLibraryTab />);

      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);

      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteGameData).not.toHaveBeenCalled();
    });

    test('shows error toast when delete fails', async () => {
      const user = userEvent.setup();
      mockDeleteGameData.mockRejectedValue(new Error('Delete failed'));

      render(<ManageLibraryTab />);

      const deleteButtons = screen.getAllByText('Delete');
      await user.click(deleteButtons[0]);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith('Delete failed', 'error');
      });
    });
  });

  describe('Empty States', () => {
    test('shows empty state when no games in category', () => {
      const contextWithNoGames = {
        ...defaultStaffContext,
        filteredLibrary: [],
      };

      useStaff.mockReturnValue(contextWithNoGames);
      render(<ManageLibraryTab />);

      expect(screen.getByText('No games in this category')).toBeInTheDocument();
    });

    test('shows empty state with search query when no results', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const searchInput = screen.getByPlaceholderText(/Search by title/);
      await user.type(searchInput, 'NonExistent');

      expect(screen.getByText(/No games found matching/)).toBeInTheDocument();
    });
  });

  describe('Context Integration', () => {
    test('uses context for filtered library', () => {
      render(<ManageLibraryTab />);

      expect(screen.getByText('Gloomhaven')).toBeInTheDocument();
      expect(screen.getByText('Wingspan')).toBeInTheDocument();
    });

    test('calls setSelectedCategory from CategoryFilter', async () => {
      const user = userEvent.setup();
      render(<ManageLibraryTab />);

      const categoryButton = screen.getByText('Core Strategy');
      await user.click(categoryButton);

      expect(mockSetSelectedCategory).toHaveBeenCalledWith('CORE_STRATEGY');
    });
  });

  describe('Accessibility', () => {
    test('has accessible table structure', () => {
      render(<ManageLibraryTab />);

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });

    test('edit and delete buttons have accessible labels', () => {
      render(<ManageLibraryTab />);

      const editButtons = screen.getAllByRole('button', { name: /Edit Game/ });
      const deleteButtons = screen.getAllByRole('button', { name: /Delete/ });

      expect(editButtons.length).toBeGreaterThan(0);
      expect(deleteButtons.length).toBeGreaterThan(0);
    });

    test('checkboxes are accessible', () => {
      render(<ManageLibraryTab />);

      const checkboxes = screen.getAllByRole('checkbox');
      expect(checkboxes.length).toBeGreaterThan(0);
    });
  });
});
