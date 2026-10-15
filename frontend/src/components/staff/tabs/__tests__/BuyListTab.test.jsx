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
  reorderBuyList: vi.fn(),
  suggestBuyListGames: vi.fn(),
  getHLStockSignals: vi.fn(),
  linkHLStockSignal: vi.fn(),
  dismissHLStockSignal: vi.fn(),
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

      // The heading above renders immediately; the gap data it summarizes
      // resolves asynchronously, so wait for that too rather than assuming
      // it's already there once the heading is.
      await waitFor(() => {
        expect(screen.getByText(/Party & Icebreakers/)).toBeInTheDocument();
      });
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

      await user.type(screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL'), '174430');
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
      await user.type(screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL'), '-123');
      await user.click(screen.getByText('Add to List'));

      await waitFor(() => {
        expect(screen.getByText('Please enter a valid BGG ID or BoardGameGeek URL')).toBeInTheDocument();
      });
      expect(apiClient.addToBuyList).not.toHaveBeenCalled();
    });

    test('accepts a pasted BoardGameGeek URL in place of a bare ID', async () => {
      const user = userEvent.setup();
      apiClient.addToBuyList.mockResolvedValue({});
      render(<BuyListTab />);

      await user.click(screen.getByText('+ Add Game'));
      await user.type(
        screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL'),
        'https://boardgamegeek.com/boardgame/174430/gloomhaven'
      );
      await user.click(screen.getByText('Add to List'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith(
          expect.objectContaining({ bgg_id: 174430 })
        );
      });
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

    test('surfaces errors and error_details count from a partial import', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.bulkImportBuyListCSV.mockResolvedValue({
        added: 1, updated: 0, skipped: 0, errors: 2,
        error_details: ['row 2: bad bgg_id', 'row 3: BGG fetch failed'],
      });

      const { container } = render(<BuyListTab />);

      await user.click(screen.getByText('📥 Bulk Import CSV'));
      const file = new File(['bgg_id\nbad'], 'test.csv', { type: 'text/csv' });
      await user.upload(container.querySelector('input[type="file"]'), file);

      await waitFor(() => {
        expect(screen.getByText(/2 errors \(see console for details\)/)).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('handles CSV import failure', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.bulkImportBuyListCSV.mockRejectedValue({
        response: { data: { detail: 'Invalid CSV format' } },
      });

      const { container } = render(<BuyListTab />);

      await user.click(screen.getByText('📥 Bulk Import CSV'));
      const file = new File(['bad data'], 'test.csv', { type: 'text/csv' });
      await user.upload(container.querySelector('input[type="file"]'), file);

      await waitFor(() => {
        expect(screen.getByText('Invalid CSV format')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('closes the bulk import modal', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await user.click(screen.getByText('📥 Bulk Import CSV'));
      await waitFor(() => {
        expect(screen.getByText('Bulk Import Games to Add from CSV')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Close'));

      await waitFor(() => {
        expect(screen.queryByText('Bulk Import Games to Add from CSV')).not.toBeInTheDocument();
      });
    });
  });

  describe('Add Game Modal - cancel and errors', () => {
    test('closes the add modal via Cancel and clears the form', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await user.click(screen.getByText('+ Add Game'));
      await user.type(screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL'), '174430');
      await user.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(screen.queryByText('Add a Candidate Game by BGG ID')).not.toBeInTheDocument();
      });

      // Re-opening should show the cleared form, not the stale value
      await user.click(screen.getByText('+ Add Game'));
      expect(screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL')).toHaveValue('');
    });

    test('handles add game error from the server', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.addToBuyList.mockRejectedValue({
        response: { data: { detail: 'Game not found' } },
      });

      render(<BuyListTab />);

      await user.click(screen.getByText('+ Add Game'));
      await user.type(screen.getByPlaceholderText('e.g., 174430 or a boardgamegeek.com/boardgame/... URL'), '999999');
      await user.click(screen.getByText('Add to List'));

      await waitFor(() => {
        expect(screen.getByText('Game not found')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Error loading gaps', () => {
    test('logs but does not crash when gap analysis fails to load', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.getLibraryGaps.mockRejectedValue(new Error('Network error'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });
      expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to load library gaps:', expect.any(Error));

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Banner dismissal', () => {
    test('dismisses the error banner', async () => {
      const user = userEvent.setup();
      apiClient.getBuyListGames.mockRejectedValue(new Error('Network error'));
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load games to add')).toBeInTheDocument();
      });

      await user.click(screen.getByLabelText('Dismiss error'));

      await waitFor(() => {
        expect(screen.queryByText('Failed to load games to add')).not.toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('dismisses the success banner', async () => {
      const user = userEvent.setup();
      apiClient.removeFromBuyList.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Remove'));

      await waitFor(() => {
        expect(screen.getByText('Removed from the list')).toBeInTheDocument();
      });

      await user.click(screen.getByLabelText('Dismiss message'));

      await waitFor(() => {
        expect(screen.queryByText('Removed from the list')).not.toBeInTheDocument();
      });
    });
  });

  describe('Error handling for edit/remove/move-to-owned', () => {
    test('does not remove when the confirmation is cancelled', async () => {
      const user = userEvent.setup();
      window.confirm = vi.fn(() => false);

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Remove'));

      expect(apiClient.removeFromBuyList).not.toHaveBeenCalled();
    });

    test('handles remove failure', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.removeFromBuyList.mockRejectedValue(new Error('Remove failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Remove'));

      await waitFor(() => {
        expect(screen.getByText('Failed to remove')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('handles save-edit failure', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.updateBuyListGame.mockRejectedValue(new Error('Save failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Edit'));
      await user.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(screen.getByText('Failed to update')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('edits the notes field', async () => {
      const user = userEvent.setup();
      apiClient.updateBuyListGame.mockResolvedValue({});

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Edit'));
      const notesInput = screen.getByDisplayValue('Worth considering');
      await user.clear(notesInput);
      await user.type(notesInput, 'Updated note');
      await user.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(apiClient.updateBuyListGame).toHaveBeenCalledWith(
          1, expect.objectContaining({ notes: 'Updated note' })
        );
      });
    });

    test('does not move to owned when confirmation is cancelled', async () => {
      const user = userEvent.setup();
      window.confirm = vi.fn(() => false);

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('→ Owned'));

      expect(apiClient.updateGame).not.toHaveBeenCalled();
    });

    test('handles move-to-owned failure', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      apiClient.updateGame.mockRejectedValue(new Error('Move failed'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('→ Owned'));

      await waitFor(() => {
        expect(screen.getByText('Failed to move game to owned collection')).toBeInTheDocument();
      });

      consoleErrorSpy.mockRestore();
    });

    test('reports success but flags a failed BGG refresh after move-to-owned', async () => {
      const user = userEvent.setup();
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      apiClient.updateGame.mockResolvedValue({});
      apiClient.updateBuyListGame.mockResolvedValue({});
      apiClient.importFromBGG.mockRejectedValueOnce(new Error('BGG unreachable'));

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      await user.click(screen.getByText('→ Owned'));

      await waitFor(() => {
        expect(screen.getByText(/BGG data refresh failed/)).toBeInTheDocument();
      });

      consoleWarnSpy.mockRestore();
    });
  });

  describe('Gap-match badges', () => {
    test('renders nothing when the candidate has no gap_match', async () => {
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, gap_match: null }],
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      expect(screen.queryByText('Fills category gap')).not.toBeInTheDocument();
    });

    test('renders nothing when gap_match has no matches', async () => {
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{
          ...mockBuyListItem,
          gap_match: { category_is_gap: false, matching_player_count_gaps: [] },
        }],
      });

      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      expect(screen.queryByText('Fills category gap')).not.toBeInTheDocument();
    });
  });

  describe('Sort by gaps filled', () => {
    test('selecting Gaps Filled defaults to descending order', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      apiClient.getBuyListGames.mockClear();
      await user.selectOptions(screen.getByDisplayValue('Rank'), 'gaps_filled');

      await waitFor(() => {
        expect(apiClient.getBuyListGames).toHaveBeenCalledWith(
          expect.objectContaining({ sort_by: 'gaps_filled', sort_desc: true })
        );
      });
      expect(screen.getByText('↓ Desc')).toBeInTheDocument();
    });
  });

  describe('Re-rank', () => {
    test('re-ranks from the current order and switches sort back to Rank', async () => {
      const user = userEvent.setup();
      const secondItem = { ...mockBuyListItem, id: 2, title: 'Second Game' };
      apiClient.getBuyListGames.mockResolvedValue({ items: [mockBuyListItem, secondItem] });
      apiClient.reorderBuyList.mockResolvedValue({
        items: [
          { ...mockBuyListItem, rank: 1 },
          { ...secondItem, rank: 2 },
        ],
      });

      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔢 Re-rank from this order'));

      await waitFor(() => {
        expect(apiClient.reorderBuyList).toHaveBeenCalledWith([1, 2]);
      });
      expect(screen.getByText('Re-ranked 2 game(s)')).toBeInTheDocument();
    });

    test('re-rank button is disabled when the list is empty', async () => {
      apiClient.getBuyListGames.mockResolvedValue({ items: [] });
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('🔢 Re-rank from this order')).toBeDisabled();
      });
    });

    test('does nothing when the confirm dialog is declined', async () => {
      const user = userEvent.setup();
      window.confirm = vi.fn(() => false);
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔢 Re-rank from this order'));

      expect(apiClient.reorderBuyList).not.toHaveBeenCalled();
    });
  });

  describe('Suggest Additional Games', () => {
    const mockSuggestion = {
      title: 'Wingspan',
      year: 2019,
      category_key: 'GATEWAY_STRATEGY',
      reason: 'Fits the gateway strategy gap.',
      suggested_bgg_id: 266192,
      suggested_bgg_title: 'Wingspan',
      suggested_bgg_year: 2019,
      bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Wingspan',
    };
    const unresolvedSuggestion = {
      title: 'Obscure Game',
      year: null,
      category_key: null,
      reason: 'Hard to pin down on BGG.',
      suggested_bgg_id: null,
      suggested_bgg_title: null,
      suggested_bgg_year: null,
      bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Obscure+Game',
    };

    test('requests and renders suggestions', async () => {
      const user = userEvent.setup();
      apiClient.suggestBuyListGames.mockResolvedValue({ suggestions: [mockSuggestion] });
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));

      expect(await screen.findByText('Wingspan (2019)')).toBeInTheDocument();
      expect(screen.getByText('Fits the gateway strategy gap.')).toBeInTheDocument();
      expect(screen.getByText(/Matched: Wingspan/)).toBeInTheDocument();
      expect(screen.getByText('💡 Suggest More')).toBeInTheDocument();
    });

    test('shows an error when no suggestions come back', async () => {
      apiClient.suggestBuyListGames.mockResolvedValue({ suggestions: [] });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));

      expect(await screen.findByText(/didn't return any suggestions/)).toBeInTheDocument();
    });

    test('shows the API error message on failure', async () => {
      apiClient.suggestBuyListGames.mockRejectedValue({
        response: { data: { detail: 'ANTHROPIC_API_KEY is not configured' } },
      });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));

      expect(await screen.findByText('ANTHROPIC_API_KEY is not configured')).toBeInTheDocument();
    });

    test('adds a resolved suggestion to the list with one click', async () => {
      apiClient.suggestBuyListGames.mockResolvedValue({ suggestions: [mockSuggestion] });
      apiClient.addToBuyList.mockResolvedValue({});
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));
      await screen.findByText('Wingspan (2019)');

      await user.click(screen.getByText('+ Add to List'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 266192,
          notes: 'Fits the gateway strategy gap.',
        });
      });
      expect(await screen.findByText('Added "Wingspan" to the list')).toBeInTheDocument();
      expect(screen.queryByText('Wingspan (2019)')).not.toBeInTheDocument();
    });

    test('unresolved suggestions open the manual Add Game modal with notes prefilled', async () => {
      apiClient.suggestBuyListGames.mockResolvedValue({ suggestions: [unresolvedSuggestion] });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));
      await screen.findByText('Obscure Game');
      expect(screen.getByText(/No confident BGG match/)).toBeInTheDocument();

      await user.click(screen.getByText('+ Add Manually'));

      expect(await screen.findByText('Add a Candidate Game by BGG ID')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Hard to pin down on BGG.')).toBeInTheDocument();
    });

    test('dismissing a suggestion removes its card', async () => {
      apiClient.suggestBuyListGames.mockResolvedValue({ suggestions: [mockSuggestion] });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('💡 Suggest Additional Games'));
      await screen.findByText('Wingspan (2019)');

      await user.click(screen.getByLabelText('Dismiss suggestion: Wingspan'));

      expect(screen.queryByText('Wingspan (2019)')).not.toBeInTheDocument();
    });
  });

  describe('HL Stock Signals', () => {
    const unmatchedSignal = {
      hl_internal_id: 501,
      hl_product_name: 'Completely New Game',
      units_sold: 7,
      current_stock: 3,
      last_sale_date: '2026-10-01',
      match_status: 'unmatched',
      match_confidence: null,
      linked_game: null,
    };
    const linkedSignal = {
      hl_internal_id: 502,
      hl_product_name: 'Wingspan Euro Expansion',
      units_sold: 4,
      current_stock: 2,
      last_sale_date: '2026-10-05',
      match_status: 'linked',
      match_confidence: 91,
      linked_game: { id: 77, title: 'Wingspan: European Expansion', status: 'WISHLIST', bgg_id: 266192 },
    };

    test('checking HL stock renders matched and unmatched candidates', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unmatchedSignal, linkedSignal] });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));

      expect(await screen.findByText('Completely New Game')).toBeInTheDocument();
      expect(screen.getByText(/No match found in this library/)).toBeInTheDocument();
      expect(screen.getByText('Wingspan Euro Expansion')).toBeInTheDocument();
      expect(screen.getByText(/Matches: Wingspan: European Expansion/)).toBeInTheDocument();
      expect(screen.getByText('🔄 Refresh')).toBeInTheDocument();
    });

    test('shows the API error message on failure', async () => {
      apiClient.getHLStockSignals.mockRejectedValue({
        response: { data: { detail: 'HL_STOCK_DATABASE_URL not configured' } },
      });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));

      expect(await screen.findByText('HL_STOCK_DATABASE_URL not configured')).toBeInTheDocument();
    });

    test('adding a matched signal adds it to the list directly', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [linkedSignal] });
      apiClient.addToBuyList.mockResolvedValue({});
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Wingspan Euro Expansion');

      await user.click(screen.getByText('+ Add to List'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 266192,
          notes: 'Selling well at HL Timaru (4 sold, 2 in stock)',
        });
      });
      expect(await screen.findByText(/Added "Wingspan: European Expansion" to the list/)).toBeInTheDocument();
      expect(screen.queryByText('Wingspan Euro Expansion')).not.toBeInTheDocument();
    });

    test('adding an unmatched signal opens the manual Add Game modal with notes prefilled', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unmatchedSignal] });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Completely New Game');

      await user.click(screen.getByText('+ Add to List'));

      expect(await screen.findByText('Add a Candidate Game by BGG ID')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Selling well at HL Timaru (7 sold, 3 in stock)')).toBeInTheDocument();
    });

    test('dismissing a signal removes its card', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unmatchedSignal] });
      apiClient.dismissHLStockSignal.mockResolvedValue({ dismissed: true });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Completely New Game');

      await user.click(screen.getByLabelText('Dismiss: Completely New Game'));

      await waitFor(() => expect(apiClient.dismissHLStockSignal).toHaveBeenCalledWith(501));
      expect(screen.queryByText('Completely New Game')).not.toBeInTheDocument();
    });

    test('confirming a fuzzy match marks it as confirmed', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [linkedSignal] });
      apiClient.linkHLStockSignal.mockResolvedValue({ hl_internal_id: 502, linked_game_id: 77 });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Wingspan Euro Expansion');
      expect(screen.getByText(/91% match - unconfirmed/)).toBeInTheDocument();

      await user.click(screen.getByText('✓ Confirm match'));

      await waitFor(() => expect(apiClient.linkHLStockSignal).toHaveBeenCalledWith(502, 77));
      expect(await screen.findByText(/Matches: Wingspan: European Expansion \(confirmed\)/)).toBeInTheDocument();
    });

    test('manually linking an unmatched signal by game ID removes its card', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unmatchedSignal] });
      apiClient.linkHLStockSignal.mockResolvedValue({ hl_internal_id: 501, linked_game_id: 101 });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Completely New Game');

      await user.type(screen.getByPlaceholderText(/Library game ID/), '101');
      await user.click(screen.getByText('Link'));

      await waitFor(() => expect(apiClient.linkHLStockSignal).toHaveBeenCalledWith(501, 101));
      expect(screen.queryByText('Completely New Game')).not.toBeInTheDocument();
    });
  });
});
