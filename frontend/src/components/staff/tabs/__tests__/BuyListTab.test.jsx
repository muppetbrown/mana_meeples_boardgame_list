/**
 * BuyListTab tests - gap-aware "games to add" list (no price tracking)
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BuyListTab } from '../BuyListTab';
import * as apiClient from '../../../../api/client';
import { useStaff } from '../../../../context/StaffContext';

// BuyListTab only needs useConfirm (kept working via the real fallback to
// window.confirm, same as before this mock existed) and the already-loaded
// library list (for the HL-signals manual-link title search).
vi.mock('../../../../context/StaffContext', () => ({
  useConfirm: () => async (options = {}) =>
    window.confirm([options?.title, options?.message].filter(Boolean).join('\n\n')),
  useStaff: vi.fn(),
}));

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
  getTrendingGames: vi.fn(),
  getAwardWinners: vi.fn(),
  searchDistroCodes: vi.fn(),
  linkGameToDistroCode: vi.fn(),
  unlinkGameDistroCode: vi.fn(),
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
      complexity_is_gap: true,
      playtime_is_gap: true,
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
    complexity_gaps: [
      { complexity_band: 'light', count: 0, pct_of_collection: 0.0, is_gap: true },
      { complexity_band: 'heavy', count: 10, pct_of_collection: 100.0, is_gap: false },
    ],
    playtime_gaps: [
      { playtime_band: 'quick', count: 0, pct_of_collection: 0.0, is_gap: true },
      { playtime_band: 'epic', count: 10, pct_of_collection: 100.0, is_gap: false },
    ],
  };

  const mockLibrary = [
    { id: 201, title: 'Catan', year: 1995 },
    { id: 202, title: 'Catan: Seafarers', year: 1997 },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    global.window.confirm = vi.fn(() => true);
    useStaff.mockReturnValue({ library: mockLibrary });

    apiClient.getBuyListGames.mockResolvedValue(mockBuyListData);
    apiClient.getLibraryGaps.mockResolvedValue(mockGaps);
    apiClient.getTrendingGames.mockResolvedValue({ trending: [] });
    apiClient.getAwardWinners.mockResolvedValue({ award_winners: [] });
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

      // 'Where the collection is thin' is a static heading rendered even
      // during loading; wait on the gap data itself instead, since it
      // resolves asynchronously and races with other panels' own loads.
      await waitFor(() => {
        expect(screen.getByText(/Party & Icebreakers/)).toBeInTheDocument();
      });

      expect(screen.getByText('Where the collection is thin')).toBeInTheDocument();
      expect(screen.getAllByText(/9\+ players/).length).toBeGreaterThan(0);
      expect(screen.getByText(/Light \(under 2\.0\)/)).toBeInTheDocument();
      expect(screen.getByText(/Quick \(under 30 min\)/)).toBeInTheDocument();
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
      expect(screen.getByText('Fills complexity gap')).toBeInTheDocument();
      expect(screen.getByText('Fills playtime gap')).toBeInTheDocument();
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

  describe('Distributor availability', () => {
    const inStock = {
      status: 'in_stock',
      options: [
        {
          distributor: 'VR', distro_code: 'V1', distro_product_name: 'Test Game',
          cost_price_ex_gst: 42.5, qty_available: 5, match_score: 100,
        },
      ],
    };
    const unlisted = { status: 'not_listed', options: [] };

    test('shows per-distributor stock and cost', async () => {
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, distro_availability: inStock }],
      });
      render(<BuyListTab />);
      expect(await screen.findByText('VR: 5 in stock · $42.50 ex GST')).toBeInTheDocument();
    });

    test('flags games no distributor lists, and can filter to them', async () => {
      const user = userEvent.setup();
      apiClient.getBuyListGames.mockResolvedValue({
        items: [
          { ...mockBuyListItem, distro_availability: inStock },
          { ...mockBuyListItem, id: 2, title: 'Gone Game', distro_availability: unlisted },
        ],
      });
      render(<BuyListTab />);
      expect(await screen.findByText('Not listed by any distributor', { selector: 'span' })).toBeInTheDocument();

      await user.selectOptions(screen.getByLabelText('Distributor'), 'unavailable');

      expect(screen.getByText('Gone Game')).toBeInTheDocument();
      expect(screen.queryByText('Test Game')).not.toBeInTheDocument();
    });

    test('shows nothing when availability is unknown', async () => {
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, distro_availability: null }],
      });
      render(<BuyListTab />);
      await screen.findByText('Test Game');
      expect(screen.queryByText(/Not listed by any distributor/, { selector: 'span' })).not.toBeInTheDocument();
    });
  });

  describe('Manual distributor links', () => {
    const unlisted = { status: 'not_listed', options: [] };
    const row = {
      distributor: 'VR',
      distro_code: 'V9',
      distro_product_name: 'OBSC GME EURO',
      cost_price_ex_gst: 30,
      qty_available: 4,
    };
    const linkedAvailability = {
      status: 'in_stock',
      options: [{ ...row, link_id: 7, match_score: null }],
    };

    test('searches the catalogue, links a code and updates the item', async () => {
      const user = userEvent.setup();
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, distro_availability: unlisted }],
      });
      apiClient.searchDistroCodes.mockResolvedValue({ items: [row] });
      apiClient.linkGameToDistroCode.mockResolvedValue({
        link_id: 7,
        distro_availability: linkedAvailability,
      });
      render(<BuyListTab />);
      await user.click(await screen.findByRole('button', { name: /Distro/ }));

      expect(await screen.findByText('OBSC GME EURO')).toBeInTheDocument();
      expect(apiClient.searchDistroCodes).toHaveBeenCalledWith('Test Game');

      await user.click(screen.getByRole('button', { name: 'Link' }));

      await waitFor(() =>
        expect(apiClient.linkGameToDistroCode).toHaveBeenCalledWith(101, 'VR', 'V9')
      );
      expect(await screen.findByText(/🔗 VR: 4 in stock/)).toBeInTheDocument();
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    test('shows the API error when linking fails', async () => {
      const user = userEvent.setup();
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, distro_availability: unlisted }],
      });
      apiClient.searchDistroCodes.mockResolvedValue({ items: [row] });
      apiClient.linkGameToDistroCode.mockRejectedValue({
        response: { data: { detail: 'That code is already linked to this game' } },
      });
      render(<BuyListTab />);
      await user.click(await screen.findByRole('button', { name: /Distro/ }));
      await user.click(await screen.findByRole('button', { name: 'Link' }));

      expect(await screen.findByText('That code is already linked to this game')).toBeInTheDocument();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    test('unlinks a manual link from its badge', async () => {
      const user = userEvent.setup();
      apiClient.getBuyListGames.mockResolvedValue({
        items: [{ ...mockBuyListItem, distro_availability: linkedAvailability }],
      });
      apiClient.unlinkGameDistroCode.mockResolvedValue({ id: 7, distro_availability: unlisted });
      render(<BuyListTab />);

      await user.click(await screen.findByRole('button', { name: /Unlink VR V9/ }));

      await waitFor(() => expect(apiClient.unlinkGameDistroCode).toHaveBeenCalledWith(7));
      expect(await screen.findByText('Not listed by any distributor', { selector: 'span' })).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    test('changes sort field', async () => {
      const user = userEvent.setup();
      render(<BuyListTab />);

      await waitFor(() => {
        expect(screen.getByText('Test Game')).toBeInTheDocument();
      });

      const sortBySelect = screen.getByLabelText('Sort By');
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

    test('shows gap fit and the BGG match used to score it', async () => {
      const scored = {
        ...unmatchedSignal,
        fit: {
          scored: true,
          source: 'bgg',
          gaps_filled: 2,
          gap_match: {
            category_is_gap: true,
            matching_player_count_gaps: [],
            complexity_is_gap: true,
            playtime_is_gap: false,
          },
          bgg: { bgg_id: 321, title: 'Completely New Game', year: 2024, match_score: 88.4 },
        },
      };
      apiClient.getHLStockSignals.mockResolvedValue({ items: [scored], scoring_pending: 0 });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));

      expect(await screen.findByText('Fills 2 gaps')).toBeInTheDocument();
      const card = screen.getByText('Completely New Game', { selector: 'div' }).closest('.border');
      expect(within(card).getByText('Fills category gap')).toBeInTheDocument();
      expect(within(card).getByText('Fills complexity gap')).toBeInTheDocument();
      const bggLink = within(card).getByRole('link', { name: 'Completely New Game (2024)' });
      expect(bggLink).toHaveAttribute('href', 'https://boardgamegeek.com/boardgame/321');
      expect(within(card).getByText(/88% name match/)).toBeInTheDocument();
    });

    test('unscored items and pending lookups are flagged', async () => {
      const unscored = {
        ...unmatchedSignal,
        fit: { scored: false, source: null, gaps_filled: null, gap_match: null, bgg: null },
      };
      const noFit = {
        ...linkedSignal,
        fit: { scored: true, source: 'library', gaps_filled: 0, gap_match: null, bgg: null },
      };
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unscored, noFit], scoring_pending: 3 });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));

      expect(await screen.findByText(/Looking up 3 more games on BoardGameGeek/)).toBeInTheDocument();
      expect(screen.getByText('Not scored yet')).toBeInTheDocument();
      expect(screen.getByText("Doesn't fill any current gaps")).toBeInTheDocument();
    });

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

      await user.click(screen.getByText('Not suitable for library'));

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

    test('manually linking an unmatched signal via title search removes its card', async () => {
      apiClient.getHLStockSignals.mockResolvedValue({ items: [unmatchedSignal] });
      apiClient.linkHLStockSignal.mockResolvedValue({ hl_internal_id: 501, linked_game_id: 201 });
      const user = userEvent.setup();
      render(<BuyListTab />);
      await waitFor(() => expect(screen.getByText('Test Game')).toBeInTheDocument());

      await user.click(screen.getByText('🔄 Check HL Stock'));
      await screen.findByText('Completely New Game');

      await user.type(screen.getByPlaceholderText(/Search library by title/), 'Catan');
      await user.click(screen.getByText('Catan (1995)'));

      await waitFor(() => expect(apiClient.linkHLStockSignal).toHaveBeenCalledWith(501, 201));
      expect(screen.queryByText('Completely New Game')).not.toBeInTheDocument();
    });
  });

  describe('Trending on BoardGameGeek', () => {
    const trendingNew = {
      bgg_id: 174430, rank: 1, title: 'Gloomhaven', year: 2017,
      thumbnail_url: 'https://example.com/thumb.jpg', status: 'new',
    };
    const trendingOwned = {
      bgg_id: 266192, rank: 2, title: 'Wingspan', year: 2019,
      thumbnail_url: null, status: 'owned',
    };
    const trendingQueued = {
      bgg_id: 1, rank: 3, title: 'Catan', year: 1995,
      thumbnail_url: null, status: 'on_buy_list',
    };

    test('loads and renders trending games on mount', async () => {
      apiClient.getTrendingGames.mockResolvedValue({ trending: [trendingNew, trendingOwned] });
      render(<BuyListTab />);

      expect(await screen.findByText('Gloomhaven')).toBeInTheDocument();
      expect(screen.getByText('Wingspan')).toBeInTheDocument();
      expect(screen.getByText('Owned')).toBeInTheDocument();
      expect(apiClient.getTrendingGames).toHaveBeenCalledWith(20);
    });

    test('shows status badges and only offers Add for new games', async () => {
      apiClient.getTrendingGames.mockResolvedValue({
        trending: [trendingNew, trendingOwned, trendingQueued],
      });
      render(<BuyListTab />);

      await screen.findByText('Gloomhaven');
      expect(screen.getByText('Owned')).toBeInTheDocument();
      expect(screen.getByText('On list')).toBeInTheDocument();
      expect(screen.getByText('+ Add')).toBeInTheDocument(); // only the "new" one
    });

    test('shows an error banner when the trending fetch fails', async () => {
      apiClient.getTrendingGames.mockRejectedValue(new Error('network error'));
      render(<BuyListTab />);

      expect(await screen.findByText(/Failed to load trending games/)).toBeInTheDocument();
    });

    test('shows empty state when there is no trending data', async () => {
      apiClient.getTrendingGames.mockResolvedValue({ trending: [] });
      render(<BuyListTab />);

      expect(await screen.findByText(/No trending data available/)).toBeInTheDocument();
    });

    test('adds a trending game and flips its status to on list', async () => {
      apiClient.getTrendingGames.mockResolvedValue({ trending: [trendingNew] });
      apiClient.addToBuyList.mockResolvedValue({});
      const user = userEvent.setup();
      render(<BuyListTab />);

      await screen.findByText('Gloomhaven');
      await user.click(screen.getByText('+ Add'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 174430,
          notes: 'Trending on BoardGameGeek (#1)',
        });
      });
      expect(await screen.findByText('Added "Gloomhaven" to the list')).toBeInTheDocument();
      expect(await screen.findByText('On list')).toBeInTheDocument();
      expect(screen.queryByText('+ Add')).not.toBeInTheDocument();
    });

    test('refresh button re-fetches trending games', async () => {
      apiClient.getTrendingGames.mockResolvedValue({ trending: [trendingNew] });
      const user = userEvent.setup();
      render(<BuyListTab />);

      await screen.findByText('Gloomhaven');
      apiClient.getTrendingGames.mockClear();

      const trendingSection = screen.getByText('🔥 Trending on BoardGameGeek').closest('.shadow');
      await user.click(within(trendingSection).getByText('↻ Refresh'));

      await waitFor(() => expect(apiClient.getTrendingGames).toHaveBeenCalledTimes(1));
    });
  });

  describe('Award Winners', () => {
    const winnerNew = {
      year: 2024, award: 'spiel_des_jahres', award_label: 'Spiel des Jahres',
      title: 'Sky Team', bgg_id: 373106, thumbnail_url: 'https://example.com/skyteam.jpg',
      status: 'new', bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Sky+Team',
    };
    const winnerOwned = {
      year: 2019, award: 'kennerspiel_des_jahres', award_label: 'Kennerspiel des Jahres',
      title: 'Wingspan', bgg_id: 266192, thumbnail_url: null,
      status: 'owned', bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Wingspan',
    };
    const winnerQueued = {
      year: 1995, award: 'spiel_des_jahres', award_label: 'Spiel des Jahres',
      title: 'Catan', bgg_id: 13, thumbnail_url: null,
      status: 'on_buy_list', bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Catan',
    };
    const winnerUnresolved = {
      year: 2017, award: 'kennerspiel_des_jahres', award_label: 'Kennerspiel des Jahres',
      title: 'Exit: The Game – The Abandoned Cabin', bgg_id: null, thumbnail_url: null,
      status: 'new', bgg_search_url: 'https://boardgamegeek.com/geeksearch.php?action=search&objecttype=boardgame&q=Exit',
    };

    test('loads and renders award winners on mount', async () => {
      apiClient.getAwardWinners.mockResolvedValue({ award_winners: [winnerNew, winnerOwned] });
      render(<BuyListTab />);

      expect(await screen.findByText('Sky Team')).toBeInTheDocument();
      expect(screen.getByText('Wingspan')).toBeInTheDocument();
      expect(screen.getByText('Owned')).toBeInTheDocument();
      expect(apiClient.getAwardWinners).toHaveBeenCalledWith(6);
    });

    test('shows status badges and only offers Add for new games with a resolved bgg_id', async () => {
      apiClient.getAwardWinners.mockResolvedValue({
        award_winners: [winnerNew, winnerOwned, winnerQueued, winnerUnresolved],
      });
      render(<BuyListTab />);

      await screen.findByText('Sky Team');
      expect(screen.getByText('Owned')).toBeInTheDocument();
      expect(screen.getByText('On list')).toBeInTheDocument();
      expect(screen.getByText('+ Add')).toBeInTheDocument(); // only winnerNew
      expect(screen.getByText('Search BGG')).toBeInTheDocument(); // winnerUnresolved has no bgg_id
    });

    test('shows an error banner when the award winners fetch fails', async () => {
      apiClient.getAwardWinners.mockRejectedValue(new Error('network error'));
      render(<BuyListTab />);

      expect(await screen.findByText(/Failed to load award winners/)).toBeInTheDocument();
    });

    test('shows empty state when there is no award winner data', async () => {
      apiClient.getAwardWinners.mockResolvedValue({ award_winners: [] });
      render(<BuyListTab />);

      expect(await screen.findByText(/No award winner data available/)).toBeInTheDocument();
    });

    test('adds an award winner and flips its status to on list', async () => {
      apiClient.getAwardWinners.mockResolvedValue({ award_winners: [winnerNew] });
      apiClient.addToBuyList.mockResolvedValue({});
      const user = userEvent.setup();
      render(<BuyListTab />);

      await screen.findByText('Sky Team');
      await user.click(screen.getByText('+ Add'));

      await waitFor(() => {
        expect(apiClient.addToBuyList).toHaveBeenCalledWith({
          bgg_id: 373106,
          notes: 'Spiel des Jahres 2024',
        });
      });
      expect(await screen.findByText('Added "Sky Team" to the list')).toBeInTheDocument();
      expect(await screen.findByText('On list')).toBeInTheDocument();
      expect(screen.queryByText('+ Add')).not.toBeInTheDocument();
    });

    test('refresh button re-fetches award winners', async () => {
      apiClient.getAwardWinners.mockResolvedValue({ award_winners: [winnerNew] });
      const user = userEvent.setup();
      render(<BuyListTab />);

      await screen.findByText('Sky Team');
      apiClient.getAwardWinners.mockClear();

      const awardSection = screen.getByText('🏆 Award Winners').closest('.shadow');
      await user.click(within(awardSection).getByText('↻ Refresh'));

      await waitFor(() => expect(apiClient.getAwardWinners).toHaveBeenCalledTimes(1));
    });
  });
});
