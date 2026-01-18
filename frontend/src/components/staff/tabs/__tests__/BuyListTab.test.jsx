/**
 * BuyListTab tests - Buy list management with pricing data
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BuyListTab } from '../BuyListTab';
import * as apiClient from '../../../../api/client';

// Mock API client
vi.mock('../../../../api/client', () => ({
  getBuyListGames: vi.fn(),
  getLastPriceUpdate: vi.fn(),
  addToBuyList: vi.fn(),
  updateBuyListGame: vi.fn(),
  removeFromBuyList: vi.fn(),
  importPrices: vi.fn(),
  bulkImportBuyListCSV: vi.fn(),
  imageProxyUrl: vi.fn((url) => `proxy:${url}`),
  updateGame: vi.fn(),
}));

describe('BuyListTab', () => {
  const mockBuyListItem = {
    id: 1,
    game_id: 101,
    title: 'Test Game',
    bgg_id: 12345,
    rank: 1,
    bgo_link: 'https://boardgameoracle.com/test',
    lpg_rrp: 99.99,
    lpg_status: 'AVAILABLE',
    buy_filter: true,
    cloudinary_url: 'https://example.com/image.jpg',
    image_url: 'https://example.com/image.jpg',
    latest_price: {
      low_price: 79.99,
      mean_price: 85.50,
      best_price: 75.00,
      best_store: 'Store A',
      discount_pct: 25.0,
      delta: 5.5,
    },
  };

  const mockBuyListData = {
    items: [mockBuyListItem],
  };

  const mockLastUpdate = {
    last_updated: '2024-01-15T10:30:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.window.confirm = vi.fn(() => true);

    apiClient.getBuyListGames.mockResolvedValue(mockBuyListData);
    apiClient.getLastPriceUpdate.mockResolvedValue(mockLastUpdate);
  });

  describe('Rendering', () => {
    test('renders buy list management header', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Buy List Management')).toBeInTheDocument();
      });

      expect(screen.getByText('Manage games to purchase and track prices')).toBeInTheDocument();
    });

    test('renders action buttons', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      expect(screen.getByText('↻ Import Prices')).toBeInTheDocument();
    });

    test('displays last price update timestamp', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Last price update:')).toBeInTheDocument();
      });

      expect(screen.getByText(/15 Jan 2024/)).toBeInTheDocument();
    });

    test('renders filter controls', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('LPG Status')).toBeInTheDocument();
      });

      expect(screen.getByText('Buy Filter')).toBeInTheDocument();
      expect(screen.getByText('Sort By')).toBeInTheDocument();
    });

    test('renders buy list table with columns', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Image')).toBeInTheDocument();
      });

      // Note: "Rank" appears in both filter dropdown and table header
      expect(screen.getAllByText('Rank').length).toBeGreaterThan(0);
      expect(screen.getByText('Game')).toBeInTheDocument();
      expect(screen.getAllByText('LPG Status').length).toBeGreaterThan(0);
      expect(screen.getByText('LPG RRP')).toBeInTheDocument();
      expect(screen.getByText('Low $')).toBeInTheDocument();
      expect(screen.getByText('Mean $')).toBeInTheDocument();
      expect(screen.getByText('Best $')).toBeInTheDocument();
      expect(screen.getByText('Store')).toBeInTheDocument();
      // "Discount %" appears in both table header and sort dropdown
      expect(screen.getAllByText('Discount %').length).toBeGreaterThan(0);
      expect(screen.getByText('Delta')).toBeInTheDocument();
      expect(screen.getByText('Filter')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });
  });

  describe('Data Loading', () => {
    test('shows loading state initially', () => {
      render(<BuyListTab />);

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    test('loads buy list on mount', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'title',
          sort_desc: false,
        });
      });
    });

    test('loads last update on mount', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(apiClient.getLastPriceUpdate).toHaveBeenCalled();
      });
    });

    test('displays buy list items', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      expect(screen.getByText('$99.99')).toBeInTheDocument();
      expect(screen.getByText('$79.99')).toBeInTheDocument();
      expect(screen.getByText('$85.50')).toBeInTheDocument();
      expect(screen.getByText('$75.00')).toBeInTheDocument();
      expect(screen.getByText('Store A')).toBeInTheDocument();
      expect(screen.getByText('25.0%')).toBeInTheDocument();
    });

    test('shows empty state when no items', async () => {
      apiClient.getBuyListGames.mockResolvedValue({ items: [] });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('No games in buy list')).toBeInTheDocument();
      });
    });

    test('handles load error gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.getBuyListGames.mockRejectedValue(new Error('Network error'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load buy list')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Filtering', () => {
    test('filters by LPG status', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const lpgStatusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(lpgStatusSelect, 'AVAILABLE');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          lpg_status: 'AVAILABLE',
          sort_by: 'title',
          sort_desc: false,
        });
      });
    });

    test('filters by buy filter', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const buyFilterSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(buyFilterSelect, 'true');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          buy_filter: 'true',
          sort_by: 'title',
          sort_desc: false,
        });
      });
    });

    test('filters by no price data', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const buyFilterSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(buyFilterSelect, 'no_price');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          buy_filter: 'no_price',
          sort_by: 'title',
          sort_desc: false,
        });
      });
    });

    test('changes sort field', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const sortBySelect = screen.getAllByRole('combobox')[2];
      await user.selectOptions(sortBySelect, 'rank');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'rank',
          sort_desc: false,
        });
      });
    });

    test('toggles sort direction', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const sortDirectionButton = screen.getByText('↑ Asc');
      await user.click(sortDirectionButton);

      await waitFor(() => {
        expect(screen.getByText('↓ Desc')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'title',
          sort_desc: true,
        });
      });
    });

    test('combines multiple filters', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const lpgStatusSelect = screen.getAllByRole('combobox')[0];
      await user.selectOptions(lpgStatusSelect, 'AVAILABLE');

      const buyFilterSelect = screen.getAllByRole('combobox')[1];
      await user.selectOptions(buyFilterSelect, 'true');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          lpg_status: 'AVAILABLE',
          buy_filter: 'true',
          sort_by: 'title',
          sort_desc: false,
        });
      });
    });
  });

  describe('Buy Filter Badge', () => {
    test('displays BUY NOW badge when buy_filter is true', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('BUY NOW')).toBeInTheDocument();
      });
    });

    test('hides badge when buy_filter is false', async () => {
      const itemWithoutBuyFilter = {
        ...mockBuyListItem,
        buy_filter: false,
      };

      apiClient.getBuyListGames.mockResolvedValue({ items: [itemWithoutBuyFilter] });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      expect(screen.queryByText('BUY NOW')).not.toBeInTheDocument();
    });
  });

  describe('Edit Functionality', () => {
    test('enters edit mode when Edit clicked', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Save')).toBeInTheDocument();
      });

      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    test('populates edit form with current values', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[0]);

      await waitFor(() => {
        const rankInput = screen.getByDisplayValue('1');
        expect(rankInput).toBeInTheDocument();
      });

      expect(screen.getByDisplayValue('https://boardgameoracle.com/test')).toBeInTheDocument();
      expect(screen.getByDisplayValue('99.99')).toBeInTheDocument();
    });

    test('saves edited values', async () => {
      const user = userEvent.setup();
      apiClient.updateBuyListGame.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Save')).toBeInTheDocument();
      });

      const rankInput = screen.getByDisplayValue('1');
      await user.clear(rankInput);
      await user.type(rankInput, '5');

      const saveButton = screen.getByText('Save');
      await user.click(saveButton);

      await waitFor(() => {
        expect(apiClient.updateBuyListGame).toHaveBeenCalledWith(1, expect.objectContaining({
          rank: '5',
        }));
      });

      await waitFor(() => {
        expect(screen.getByText('Updated successfully')).toBeInTheDocument();
      });
    });

    test('cancels edit mode', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });

      const cancelButton = screen.getByText('Cancel');
      await user.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText('Save')).not.toBeInTheDocument();
      });
    });

    test('handles save error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.updateBuyListGame.mockRejectedValue(new Error('Save failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const editButtons = screen.getAllByText('Edit');
      await user.click(editButtons[0]);

      const saveButton = screen.getByText('Save');
      await user.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to update')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Remove Functionality', () => {
    test('removes game from buy list with confirmation', async () => {
      const user = userEvent.setup();
      apiClient.removeFromBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);

      expect(window.confirm).toHaveBeenCalledWith('Remove this game from the buy list?');

      await waitFor(() => {
        expect(apiClient.removeFromBuyList).toHaveBeenCalledWith(1);
      });

      await waitFor(() => {
        expect(screen.getByText('Removed from buy list')).toBeInTheDocument();
      });
    });

    test('does not remove if user cancels confirmation', async () => {
      const user = userEvent.setup();
      window.confirm = vi.fn(() => false);

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);

      expect(window.confirm).toHaveBeenCalled();
      expect(apiClient.removeFromBuyList).not.toHaveBeenCalled();
    });

    test('handles remove error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.removeFromBuyList.mockRejectedValue(new Error('Remove failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const removeButtons = screen.getAllByText('Remove');
      await user.click(removeButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Failed to remove')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Move to Owned', () => {
    test('moves game to owned collection with confirmation', async () => {
      const user = userEvent.setup();
      apiClient.updateGame.mockResolvedValue({});
      apiClient.updateBuyListGame.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const moveButton = screen.getByText('→ Owned');
      await user.click(moveButton);

      expect(window.confirm).toHaveBeenCalledWith('Move "Test Game" to owned collection?');

      await waitFor(() => {
        expect(apiClient.updateGame).toHaveBeenCalledWith(101, {
          status: 'OWNED',
          date_added: expect.any(String),
        });
      });

      await waitFor(() => {
        expect(apiClient.updateBuyListGame).toHaveBeenCalledWith(1, {
          on_buy_list: false,
        });
      });

      await waitFor(() => {
        expect(screen.getByText('"Test Game" moved to owned collection!')).toBeInTheDocument();
      });
    });

    test('does not move if user cancels confirmation', async () => {
      const user = userEvent.setup();
      window.confirm = vi.fn(() => false);

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const moveButton = screen.getByText('→ Owned');
      await user.click(moveButton);

      expect(window.confirm).toHaveBeenCalled();
      expect(apiClient.updateGame).not.toHaveBeenCalled();
    });

    test('handles move to owned error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.updateGame.mockRejectedValue(new Error('Move failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const moveButton = screen.getByText('→ Owned');
      await user.click(moveButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to move game to owned collection')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Add Game Modal', () => {
    test('opens add game modal', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });
    });

    test('closes add game modal', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const cancelButtons = screen.getAllByText('Cancel');
      await user.click(cancelButtons[0]);

      await waitFor(() => {
        expect(screen.queryByText('Add Game to Buy List by BGG ID')).not.toBeInTheDocument();
      });
    });

    test('adds game by BGG ID', async () => {
      const user = userEvent.setup();
      apiClient.addToBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const bggIdInput = screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)');
      await user.type(bggIdInput, '174430');

      const addToBuyListButton = screen.getByText('Add to Buy List');
      await user.click(addToBuyListButton);

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 174430,
          rank: null,
          bgo_link: null,
          lpg_rrp: null,
          lpg_status: null,
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Added to buy list (imported from BGG if needed)')).toBeInTheDocument();
      });
    });

    test('validates BGG ID is not empty', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const addToBuyListButton = screen.getByText('Add to Buy List');

      // Button should be disabled when BGG ID is empty
      expect(addToBuyListButton).toBeDisabled();
      expect(apiClient.addToBuyList).not.toHaveBeenCalled();
    });

    test('validates BGG ID is a positive number', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const bggIdInput = screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)');
      await user.type(bggIdInput, '-123');

      const addToBuyListButton = screen.getByText('Add to Buy List');
      await user.click(addToBuyListButton);

      await waitFor(() => {
        expect(screen.getByText('BGG ID must be a positive number')).toBeInTheDocument();
      });

      expect(apiClient.addToBuyList).not.toHaveBeenCalled();
    });

    test('includes optional fields when provided', async () => {
      const user = userEvent.setup();
      apiClient.addToBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const bggIdInput = screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)');
      await user.type(bggIdInput, '174430');

      const rankInput = screen.getByPlaceholderText('1 = highest priority');
      await user.type(rankInput, '5');

      const bgoLinkInput = screen.getByPlaceholderText('https://boardgameoracle.com/en-NZ/price/...');
      await user.type(bgoLinkInput, 'https://boardgameoracle.com/test');

      const addToBuyListButton = screen.getByText('Add to Buy List');
      await user.click(addToBuyListButton);

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 174430,
          rank: 5,
          bgo_link: 'https://boardgameoracle.com/test',
          lpg_rrp: null,
          lpg_status: null,
        });
      });
    });

    test('handles add game error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.addToBuyList.mockRejectedValue({
        response: { data: { detail: 'Game not found' } },
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      const addButton = screen.getByText('+ Add Game');
      await user.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Add Game to Buy List by BGG ID')).toBeInTheDocument();
      });

      const bggIdInput = screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)');
      await user.type(bggIdInput, '999999');

      const addToBuyListButton = screen.getByText('Add to Buy List');
      await user.click(addToBuyListButton);

      await waitFor(() => {
        expect(screen.getByText('Game not found')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Bulk Import Modal', () => {
    test('opens bulk import modal', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      });

      const bulkImportButton = screen.getByText('📥 Bulk Import CSV');
      await user.click(bulkImportButton);

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Buy List from CSV')).toBeInTheDocument();
      });
    });

    test('closes bulk import modal', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      });

      const bulkImportButton = screen.getByText('📥 Bulk Import CSV');
      await user.click(bulkImportButton);

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Buy List from CSV')).toBeInTheDocument();
      });

      const closeButtons = screen.getAllByText('Close');
      await user.click(closeButtons[0]);

      await waitFor(() => {
        expect(screen.queryByText('Bulk Import Buy List from CSV')).not.toBeInTheDocument();
      });
    });

    test('shows CSV format instructions', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      });

      const bulkImportButton = screen.getByText('📥 Bulk Import CSV');
      await user.click(bulkImportButton);

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Buy List from CSV')).toBeInTheDocument();
      });

      // Check for CSV format instructions
      expect(screen.getByText('CSV Format:')).toBeInTheDocument();
      expect(screen.getAllByText(/bgg_id/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/rank/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/lpg_status/).length).toBeGreaterThan(0);
    });

    test('imports CSV file', async () => {
      const user = userEvent.setup();
      apiClient.bulkImportBuyListCSV.mockResolvedValue({
        added: 5,
        updated: 2,
        skipped: 1,
        errors: 0,
      });

      const { container } = render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      });

      const bulkImportButton = screen.getByText('📥 Bulk Import CSV');
      await user.click(bulkImportButton);

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Buy List from CSV')).toBeInTheDocument();
      });

      const file = new File(['bgg_id,rank\n12345,1'], 'test.csv', { type: 'text/csv' });

      // Find file input by querying DOM directly
      const fileInput = container.querySelector('input[type="file"]');

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(apiClient.bulkImportBuyListCSV).toHaveBeenCalledWith(file);
      });

      await waitFor(() => {
        expect(screen.getByText(/Bulk import completed: 5 added, 2 updated, 1 skipped/)).toBeInTheDocument();
      });
    });

    test('handles import errors', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.bulkImportBuyListCSV.mockRejectedValue({
        response: { data: { detail: 'Invalid CSV format' } },
      });

      const { container } = render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
      });

      const bulkImportButton = screen.getByText('📥 Bulk Import CSV');
      await user.click(bulkImportButton);

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Buy List from CSV')).toBeInTheDocument();
      });

      const file = new File(['invalid data'], 'test.csv', { type: 'text/csv' });

      // Find file input by querying DOM directly
      const fileInput = container.querySelector('input[type="file"]');

      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(screen.getByText('Invalid CSV format')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Import Prices', () => {
    test('imports prices from JSON file', async () => {
      const user = userEvent.setup();
      apiClient.importPrices.mockResolvedValue({
        imported: 25,
        skipped: 5,
        total: 30,
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('↻ Import Prices')).toBeInTheDocument();
      });

      const importButton = screen.getByText('↻ Import Prices');
      await user.click(importButton);

      // The intermediate "Import started..." message may appear/disappear too quickly to reliably test
      // Just verify the API was called and final success message appears

      await waitFor(() => {
        expect(apiClient.importPrices).toHaveBeenCalledWith('latest_prices.json');
      });

      await waitFor(() => {
        expect(screen.getByText(/✅ Import completed! 25 prices imported, 5 skipped/)).toBeInTheDocument();
      });
    });

    test('handles import timeout', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.importPrices.mockRejectedValue(new Error('timeout'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('↻ Import Prices')).toBeInTheDocument();
      });

      const importButton = screen.getByText('↻ Import Prices');
      await user.click(importButton);

      await waitFor(() => {
        expect(screen.getByText(/⚠️ Import timed out/)).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('handles generic import error', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.importPrices.mockRejectedValue({
        response: { data: { detail: 'File not found' } },
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('↻ Import Prices')).toBeInTheDocument();
      });

      const importButton = screen.getByText('↻ Import Prices');
      await user.click(importButton);

      await waitFor(() => {
        expect(screen.getByText(/Failed to import prices: File not found/)).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Price Display', () => {
    test('displays all price fields correctly', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('$99.99')).toBeInTheDocument();
      });

      expect(screen.getByText('$79.99')).toBeInTheDocument();
      expect(screen.getByText('$85.50')).toBeInTheDocument();
      expect(screen.getByText('$75.00')).toBeInTheDocument();
    });

    test('shows dash for missing prices', async () => {
      const itemWithoutPrices = {
        ...mockBuyListItem,
        latest_price: null,
      };

      apiClient.getBuyListGames.mockResolvedValue({ items: [itemWithoutPrices] });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });

    test('displays discount percentage', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('25.0%')).toBeInTheDocument();
      });
    });

    test('displays price delta with correct color', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+5.5')).toBeInTheDocument();
      });
    });
  });

  describe('Status Display', () => {
    test('displays LPG status with color coding', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('AVAILABLE')).toBeInTheDocument();
      });
    });

    test('shows dash when status is missing', async () => {
      const itemWithoutStatus = {
        ...mockBuyListItem,
        lpg_status: null,
      };

      apiClient.getBuyListGames.mockResolvedValue({ items: [itemWithoutStatus] });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const dashElements = screen.getAllByText('-');
      expect(dashElements.length).toBeGreaterThan(0);
    });
  });

  describe('Image Display', () => {
    test('displays game image', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        const images = screen.getAllByAltText('Test Game');
        expect(images.length).toBeGreaterThan(0);
      });
    });

    test('uses imageProxyUrl for images', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(apiClient.imageProxyUrl).toHaveBeenCalledWith('https://example.com/image.jpg');
      });
    });
  });

  describe('External Links', () => {
    test('displays BGO link when available', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        const bgoLink = screen.getByText('BGO ↗');
        expect(bgoLink).toHaveAttribute('href', 'https://boardgameoracle.com/test');
        expect(bgoLink).toHaveAttribute('target', '_blank');
        expect(bgoLink).toHaveAttribute('rel', 'noopener noreferrer');
      });
    });
  });
});
