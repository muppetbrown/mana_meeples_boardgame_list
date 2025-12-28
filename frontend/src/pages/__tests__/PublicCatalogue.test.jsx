// frontend/src/pages/__tests__/PublicCatalogue.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import PublicCatalogue from '../PublicCatalogue';
import * as apiClient from '../../api/client';

// Mock API client
jest.mock('../../api/client');

// Mock onboarding hook
jest.mock('../../hooks/useOnboarding', () => ({
  useOnboarding: () => ({
    isFirstVisit: false,
    markHelpOpened: jest.fn(),
  }),
}));

const mockGames = {
  items: [
    {
      id: 1,
      title: 'Catan',
      mana_meeple_category: 'GATEWAY_STRATEGY',
      players_min: 3,
      players_max: 4,
      playtime_min: 60,
      playtime_max: 90,
      year: 1995,
      thumbnail_url: 'http://example.com/catan.jpg',
      complexity: 2.5,
    },
    {
      id: 2,
      title: 'Pandemic',
      mana_meeple_category: 'COOP_ADVENTURE',
      players_min: 2,
      players_max: 4,
      playtime_min: 45,
      playtime_max: 60,
      year: 2008,
      thumbnail_url: 'http://example.com/pandemic.jpg',
      complexity: 2.4,
    },
  ],
  total: 2,
  page: 1,
  page_size: 12,
};

const mockCategoryCounts = {
  GATEWAY_STRATEGY: 50,
  COOP_ADVENTURE: 30,
  CORE_STRATEGY: 40,
  KIDS_FAMILIES: 25,
  PARTY_ICEBREAKERS: 20,
};

describe('PublicCatalogue Page', () => {
  beforeEach(() => {
    apiClient.getPublicGames.mockResolvedValue(mockGames);
    apiClient.getPublicCategoryCounts.mockResolvedValue(mockCategoryCounts);

    // Mock window.scrollTo
    window.scrollTo = jest.fn();

    // Mock IntersectionObserver
    global.IntersectionObserver = class IntersectionObserver {
      constructor() {}
      disconnect() {}
      observe() {}
      unobserve() {}
      takeRecords() {
        return [];
      }
    };
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    // Should show skeleton loaders
    const skeletons = screen.getAllByTestId('skeleton-loader');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  test('renders games after loading', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
      expect(screen.getByText('Pandemic')).toBeInTheDocument();
    });
  });

  test('displays category counts', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicCategoryCounts).toHaveBeenCalled();
    });
  });

  test('filters games by search query', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    // Type in search box
    const searchBox = screen.getByPlaceholderText(/search/i);
    await user.clear(searchBox);
    await user.type(searchBox, 'Pandemic');

    // Should call API with search query after debounce
    await waitFor(
      () => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ q: 'Pandemic' })
        );
      },
      { timeout: 3000 }
    );
  });

  test('updates URL with search parameters', async () => {
    const user = userEvent.setup();

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    const searchBox = screen.getByPlaceholderText(/search/i);
    await user.type(searchBox, 'Test');

    // URL should be updated with search parameter
    await waitFor(() => {
      expect(window.location.search).toContain('q=Test');
    });
  });

  test('handles API errors gracefully', async () => {
    apiClient.getPublicGames.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  test('displays empty state when no games found', async () => {
    apiClient.getPublicGames.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
    });

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no games found/i)).toBeInTheDocument();
    });
  });

  test('renders sort select component', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/sort/i)).toBeInTheDocument();
    });
  });

  test('renders search box component', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  test('fetches games and category counts on mount', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
      expect(apiClient.getPublicCategoryCounts).toHaveBeenCalled();
    });
  });

  test('scrolls to top on mount', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  test('applies NZ designer filter from URL', async () => {
    window.history.pushState({}, '', '?nz_designer=true');

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalledWith(
        expect.objectContaining({ nz_designer: true })
      );
    });
  });

  test('applies category filter from URL', async () => {
    window.history.pushState({}, '', '?category=COOP_ADVENTURE');

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'COOP_ADVENTURE' })
      );
    });
  });

  test('applies sort order from URL', async () => {
    window.history.pushState({}, '', '?sort=title_asc');

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalledWith(
        expect.objectContaining({ sort: 'title_asc' })
      );
    });
  });

  test('displays total game count', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/2/)).toBeInTheDocument(); // Total count
    });
  });
});
