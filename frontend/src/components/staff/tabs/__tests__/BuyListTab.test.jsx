/**
 * BuyListTab tests - gap-aware "games to add" list (no price tracking)
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BuyListTab } from '../BuyListTab';
import * as apiClient from '../../../../api/client';

vi.mock('../../../../api/client', () => ({
  getBuyListGames: vi.fn(),
  getLibraryGaps: vi.fn(),
  addToBuyList: vi.fn(),
  updateBuyListGame: vi.fn(),
  removeFromBuyList: vi.fn(),
  bulkImportBuyListCSV: vi.fn(),
  imageProxyUrl: vi.fn((url) => `proxy:${url}`),
  updateGame: vi.fn(),
  importFromBGG: vi.fn().mockResolvedValue({}),
}));

describe('BuyListTab', () => {
  const mockBuyListItem = {
    id: 1,
    game_id: 101,
    title: 'Test Game',
    bgg_id: 12345,
    rank: 1,
    notes: 'Worth considering',
    cloudinary_url: 'https://example.com/image.jpg',
    image_url: 'https://example.com/image.jpg',
    mana_meeple_category: 'PARTY_ICEBREAKERS',
    players_min: 8,
    players_max: 12,
    gap_match: {
      category_is_gap: true,
      matching_player_count_gaps: ['9+'],
    },
  };

  const mockBuyListData = { items: [mockBuyListItem] };

  const mockGaps = {
    total_games: 10,
    category_gaps: [
      { category: 'PARTY_ICEBREAKERS', count: 0, pct_of_collection: 0.0, is_gap: true },
      { category: 'CORE_STRATEGY', count: 10, pct_of_collection: 100.0, is_gap: false },
    ],
    player_count_gaps: [
      { player_count: '9+', games_supporting: 0, pct_of_collection: 0.0, is_gap: true },
      { player_count: '2', games_supporting: 10, pct_of_collection: 100.0, is_gap: false },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.window.confirm = vi.fn(() => true);

    apiClient.getBuyListGames.mockResolvedValue(mockBuyListData);
    apiClient.getLibraryGaps.mockResolvedValue(mockGaps);
  });

  describe('Rendering', () => {
    test('renders header', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Games to Add')).toBeInTheDocument();
      });
    });

    test('renders action buttons', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });
      expect(screen.getByText('📥 Bulk Import CSV')).toBeInTheDocument();
    });

    test('renders table columns without price fields', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Image')).toBeInTheDocument();
      });

      expect(screen.getAllByText('Rank').length).toBeGreaterThan(0);
      expect(screen.getByText('Game')).toBeInTheDocument();
      expect(screen.getByText('Notes')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
      expect(screen.queryByText('LPG Status')).not.toBeInTheDocument();
      expect(screen.queryByText('Discount %')).not.toBeInTheDocument();
    });

    test('shows gap analysis panel', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Where the collection is thin')).toBeInTheDocument();
      });

      expect(screen.getByText(/Party & Icebreakers/)).toBeInTheDocument();
      expect(screen.getAllByText(/9\+ players/).length).toBeGreaterThan(0);
    });

    test('shows all-clear message when no gaps', async () => {
      apiClient.getLibraryGaps.mockResolvedValue({
        total_games: 10,
        category_gaps: [{ category: 'CORE_STRATEGY', count: 10, pct_of_collection: 100, is_gap: false }],
        player_count_gaps: [{ player_count: '2', games_supporting: 10, pct_of_collection: 100, is_gap: false }],
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText(/No significant gaps detected/)).toBeInTheDocument();
      });
    });
  });

  describe('Data Loading', () => {
    test('loads games to add on mount', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'rank',
          sort_desc: false,
        });
      });
    });

    test('loads library gaps on mount', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(apiClient.getLibraryGaps).toHaveBeenCalled();
      });
    });

    test('displays items with notes and gap-match badges', async () => {
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      expect(screen.getByText('Worth considering')).toBeInTheDocument();
      expect(screen.getByText('Fills category gap')).toBeInTheDocument();
      expect(screen.getByText(/Fills 9\+ players gap/)).toBeInTheDocument();
    });

    test('shows empty state when no items', async () => {
      apiClient.getBuyListGames.mockResolvedValue({ items: [] });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('No games on the list yet')).toBeInTheDocument();
      });
    });

    test('handles load error gracefully', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.getBuyListGames.mockRejectedValue(new Error('Network error'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load games to add')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Sorting', () => {
    test('changes sort field', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const sortBySelect = screen.getByRole('combobox');
      await user.selectOptions(sortBySelect, 'title');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'title',
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

      await user.click(screen.getByText('↑ Asc'));

      await waitFor(() => {
        expect(screen.getByText('↓ Desc')).toBeInTheDocument();
      });
      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith({
          sort_by: 'rank',
          sort_desc: true,
        });
      });
    });
  });

  describe('Edit Functionality', () => {
    test('enters edit mode and populates rank/notes', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Edit'));

      await waitFor(() => {
        expect(screen.getByDisplayValue('1')).toBeInTheDocument();
      });
      expect(screen.getByDisplayValue('Worth considering')).toBeInTheDocument();
    });

    test('saves edited values', async () => {
      const user = userEvent.setup();
      apiClient.updateBuyListGame.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Edit'));

      const rankInput = screen.getByDisplayValue('1');
      await user.clear(rankInput);
      await user.type(rankInput, '5');

      await user.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(apiClient.updateBuyListGame).toHaveBeenCalledWith(1, expect.objectContaining({ rank: '5' }));
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

      await user.click(screen.getByText('Edit'));
      await waitFor(() => expect(screen.getByText('Cancel')).toBeInTheDocument());
      await user.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(screen.queryByText('Save')).not.toBeInTheDocument();
      });
    });
  });

  describe('Remove Functionality', () => {
    test('removes game with confirmation', async () => {
      const user = userEvent.setup();
      apiClient.removeFromBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Remove'));

      await waitFor(() => {
        expect(apiClient.removeFromBuyList).toHaveBeenCalledWith(1);
      });
      await waitFor(() => {
        expect(screen.getByText('Removed from the list')).toBeInTheDocument();
      });
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

      await user.click(screen.getByText('→ Owned'));

      await waitFor(() => {
        expect(apiClient.updateGame).toHaveBeenCalledWith(101, {
          status: 'OWNED',
          date_added: expect.any(String),
        });
      });
      await waitFor(() => {
        expect(apiClient.updateBuyListGame).toHaveBeenCalledWith(1, { on_buy_list: false });
      });
      await waitFor(() => {
        expect(screen.getByText('"Test Game" moved to owned collection!')).toBeInTheDocument();
      });
    });
  });

  describe('Add Game Modal', () => {
    test('adds game by BGG ID with rank and notes', async () => {
      const user = userEvent.setup();
      apiClient.addToBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('+ Add Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('+ Add Game'));

      await waitFor(() => {
        expect(screen.getByText('Add a Candidate Game by BGG ID')).toBeInTheDocument();
      });

      await user.type(screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)'), '174430');
      await user.type(screen.getByPlaceholderText('1 = highest priority'), '5');
      await user.type(screen.getByPlaceholderText('Why this game is worth adding'), 'Fills a gap');

      await user.click(screen.getByText('Add to List'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 174430,
          rank: 5,
          notes: 'Fills a gap',
        });
      });
      await waitFor(() => {
        expect(screen.getByText('Added to the list (imported from BGG if needed)')).toBeInTheDocument();
      });
    });

    test('validates BGG ID is a positive number', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await user.click(screen.getByText('+ Add Game'));
      await user.type(screen.getByPlaceholderText('e.g., 174430 (Gloomhaven)'), '-123');
      await user.click(screen.getByText('Add to List'));

      await waitFor(() => {
        expect(screen.getByText('BGG ID must be a positive number')).toBeInTheDocument();
      });
      expect(apiClient.addToBuyList).not.toHaveBeenCalled();
    });
  });

  describe('Bulk Import Modal', () => {
    test('shows CSV format without price columns', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await user.click(screen.getByText('📥 Bulk Import CSV'));

      await waitFor(() => {
        expect(screen.getByText('Bulk Import Games to Add from CSV')).toBeInTheDocument();
      });

      expect(screen.getAllByText(/bgg_id/).length).toBeGreaterThan(0);
      expect(screen.queryByText(/lpg_status/)).not.toBeInTheDocument();
    });

    test('imports CSV file', async () => {
      const user = userEvent.setup();
      apiClient.bulkImportBuyListCSV.mockResolvedValue({ added: 5, updated: 2, skipped: 1, errors: 0 });

      const { container } = render(<BuyListTab />);

      await user.click(screen.getByText('📥 Bulk Import CSV'));
      await waitFor(() => {
        expect(screen.getByText('Bulk Import Games to Add from CSV')).toBeInTheDocument();
      });

      const file = new File(['bgg_id,rank,notes\n12345,1,test'], 'test.csv', { type: 'text/csv' });
      const fileInput = container.querySelector('input[type="file"]');
      await user.upload(fileInput, file);

      await waitFor(() => {
        expect(apiClient.bulkImportBuyListCSV).toHaveBeenCalledWith(file);
      });
      await waitFor(() => {
        expect(screen.getByText(/Bulk import completed: 5 added, 2 updated, 1 skipped/)).toBeInTheDocument();
      });
    });
  });
});
