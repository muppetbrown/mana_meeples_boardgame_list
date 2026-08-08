// frontend/src/pages/__tests__/PublicCatalogue.test.jsx
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, cleanup, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PublicCatalogue from '../PublicCatalogue';
import * as apiClient from '../../api/client';

vi.mock('../../api/client');

const mockGames = {
  items: [
    { id: 1, title: 'Catan', mana_meeple_category: 'GATEWAY_STRATEGY', players_min: 3, players_max: 4, playtime_min: 60, playtime_max: 120, complexity: 2.32 },
    { id: 2, title: 'Pandemic', mana_meeple_category: 'COOP_ADVENTURE', players_min: 2, players_max: 4, playtime_min: 45, playtime_max: 45, complexity: 2.43 },
  ],
  total: 2,
  page: 1,
  page_size: 12,
};

const mockCategoryCounts = {
  all: 100,
  GATEWAY_STRATEGY: 50,
  COOP_ADVENTURE: 30,
  CORE_STRATEGY: 10,
  KIDS_FAMILIES: 5,
  PARTY_ICEBREAKERS: 5,
  uncategorized: 0,
};

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  });
}

describe('PublicCatalogue Page', () => {
  let queryClient;
  let user;

  const renderWithQuery = (ui) => render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );

  const renderPage = () => renderWithQuery(
    <BrowserRouter>
      <PublicCatalogue />
    </BrowserRouter>
  );

  beforeEach(() => {
    queryClient = createTestQueryClient();
    user = userEvent.setup();
    vi.clearAllMocks();
    apiClient.getPublicGames.mockResolvedValue(mockGames);
    apiClient.getPublicCategoryCounts.mockResolvedValue(mockCategoryCounts);
    window.scrollTo = vi.fn();
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
    global.IntersectionObserver = vi.fn().mockImplementation(function (callback, options) {
      this.observe = vi.fn();
      this.disconnect = vi.fn();
      this.unobserve = vi.fn();
      this.callback = callback;
      this.options = options;
      return this;
    });
    vi.useRealTimers();
  });

  afterEach(() => {
    cleanup();
    queryClient.clear();
  });

  test('renders games after loading', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
      expect(screen.getByText('Pandemic')).toBeInTheDocument();
    });
  });

  test('fetches games and category counts on mount', async () => {
    renderPage();

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
      expect(apiClient.getPublicCategoryCounts).toHaveBeenCalled();
    });
  });

  test('scrolls to top on mount', async () => {
    renderPage();

    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
    await waitFor(() => expect(apiClient.getPublicGames).toHaveBeenCalled());
  });

  test('shows the live total from category counts in the header', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/100 games on our shelves/i)).toBeInTheDocument();
    });
  });

  test('shows the shelf picker with per-category counts', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Gateway Strategy, 50 games/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Co-op & Adventure, 30 games/i })).toBeInTheDocument();
    });
  });

  test('displays error message and retries when games fail to load', async () => {
    apiClient.getPublicGames.mockRejectedValue(new Error('Network error'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    apiClient.getPublicGames.mockResolvedValue(mockGames);
    await user.click(screen.getByRole('button', { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });
  });

  test('shows the empty state and clears filters', async () => {
    apiClient.getPublicGames.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 12 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/No games match/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /clear all filters/i }));
    expect(apiClient.getPublicGames).toHaveBeenCalled();
  });

  test('toggling a quick pick sends the quick_pick param and shows a removable chip', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Team up/i }));

    await waitFor(() => {
      const lastCall = apiClient.getPublicGames.mock.calls.at(-1)[0];
      expect(lastCall.quick_pick).toBe('coop');
    });

    const chip = screen.getByRole('button', { name: /Team up ✕/i });
    expect(chip).toBeInTheDocument();

    // Clicking the chip clears the quick pick again. Note: this returns to the
    // exact queryKey React Query already cached from the initial mount, so no
    // new getPublicGames call fires — that's correct caching behavior, not a
    // bug — so assert on the rendered state instead of a new mock call.
    await user.click(chip);

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Team up ✕/i })).not.toBeInTheDocument();
    });
    const teamUpButton = screen.getByRole('button', { name: /Team up/i });
    expect(teamUpButton).toHaveAttribute('aria-pressed', 'false');
  });

  test('shelf categories are multi-select and stack (AND) with a quick pick', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Team up/i }));
    await user.click(screen.getByRole('button', { name: /Gateway Strategy, 50 games/i }));
    await user.click(screen.getByRole('button', { name: /Co-op & Adventure, 30 games/i }));

    await waitFor(() => {
      const lastCall = apiClient.getPublicGames.mock.calls.at(-1)[0];
      expect(lastCall.quick_pick).toBe('coop');
      expect(lastCall.category).toBe('GATEWAY_STRATEGY,COOP_ADVENTURE');
    });

    expect(screen.getByRole('button', { name: /Gateway Strategy ✕/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Co-op & Adventure ✕/i })).toBeInTheDocument();
  });

  test('opens the filter sheet, applies a player filter, and closes on Show N games', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Narrow it down/i }));
    const dialog = await screen.findByRole('dialog', { name: /Narrow it down/i });

    await user.click(within(dialog).getByRole('button', { name: '6+' }));

    await waitFor(() => {
      const lastCall = apiClient.getPublicGames.mock.calls.at(-1)[0];
      expect(lastCall.players).toBe(6);
    });

    await user.click(within(dialog).getByRole('button', { name: /Show \d+ games?/i }));
    expect(screen.queryByRole('dialog', { name: /Narrow it down/i })).not.toBeInTheDocument();

    // Filter persists as a chip after closing
    expect(screen.getByRole('button', { name: /6\+ players ✕/i })).toBeInTheDocument();
  });

  test('duration and rules-crunch buckets map to the expected API params', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Narrow it down/i }));
    const dialog = await screen.findByRole('dialog', { name: /Narrow it down/i });

    await user.click(within(dialog).getByRole('button', { name: 'Under 30 min' }));
    await waitFor(() => {
      const lastCall = apiClient.getPublicGames.mock.calls.at(-1)[0];
      expect(lastCall.playtime_max_max).toBe(30);
      expect(lastCall.playtime_max_min).toBeUndefined();
    });

    await user.click(within(dialog).getByRole('button', { name: 'Easy' }));
    await waitFor(() => {
      const lastCall = apiClient.getPublicGames.mock.calls.at(-1)[0];
      expect(lastCall.complexity_max).toBeCloseTo(1.4999);
      expect(lastCall.complexity_min).toBeUndefined();
    });
  });

  test('Clear all removes every active filter', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /First timers/i }));
    await user.click(screen.getByRole('button', { name: /Kids & Families, 5 games/i }));

    expect(await screen.findByRole('button', { name: /Clear all/i })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Clear all/i }));

    // Clearing filters returns to the initial (unfiltered) queryKey, which
    // React Query already has cached from the mount — so assert on the
    // rendered state (no chips, quick-pick/shelf toggles reset) rather than
    // a new getPublicGames call.
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Clear all/i })).not.toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /First timers/i })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: /Kids & Families, 5 games/i })).toHaveAttribute('aria-pressed', 'false');
  });

  test('expands a card to show details and links to the game page', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Catan')).toBeInTheDocument());

    const moreButtons = screen.getAllByRole('button', { name: 'More info' });
    await user.click(moreButtons[0]);

    expect(await screen.findByRole('link', { name: /View full details/i })).toHaveAttribute('href', expect.stringMatching(/^\/game\/\d+$/));
  });
});
