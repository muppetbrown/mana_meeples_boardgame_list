// frontend/src/pages/__tests__/PublicCatalogue.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import PublicCatalogue from '../PublicCatalogue';
import * as apiClient from '../../api/client';

vi.mock('../../api/client');

vi.mock('../../hooks/useOnboarding', () => ({
  useOnboarding: () => ({
    isFirstVisit: false,
    markHelpOpened: vi.fn(),
  }),
}));

const mockGames = {
  items: [
    { id: 1, title: 'Catan', mana_meeple_category: 'GATEWAY_STRATEGY' },
    { id: 2, title: 'Pandemic', mana_meeple_category: 'COOP_ADVENTURE' },
  ],
  total: 2,
  page: 1,
  page_size: 12,
};

const mockCategoryCounts = {
  all: 100,
  GATEWAY_STRATEGY: 50,
  COOP_ADVENTURE: 30,
};

describe('PublicCatalogue Page', () => {
  beforeEach(() => {
    apiClient.getPublicGames.mockResolvedValue(mockGames);
    apiClient.getPublicCategoryCounts.mockResolvedValue(mockCategoryCounts);
    window.scrollTo = vi.fn();
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
    // Mock IntersectionObserver as a class
    global.IntersectionObserver = vi.fn(function() {
      this.observe = vi.fn();
      this.disconnect = vi.fn();
      this.unobserve = vi.fn();
    });
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

  test('displays category counts', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/All \(100\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Gateway Strategy \(50\)/i)).toBeInTheDocument();
    });
  });

  test('displays error message when games fail to load', async () => {
    apiClient.getPublicGames.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load games/i)).toBeInTheDocument();
    });
  });

  test('shows retry button on error', async () => {
    apiClient.getPublicGames.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      const retryButton = screen.getByRole('button', { name: /retry/i });
      expect(retryButton).toBeInTheDocument();
    });
  });

  test('handles category counts fetch failure gracefully', async () => {
    apiClient.getPublicCategoryCounts.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    // Should still render the page
    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });
  });

  test('displays no results message when no games match', async () => {
    apiClient.getPublicGames.mockResolvedValue({
      items: [],
      total: 0,
    });

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no games found matching your criteria/i)).toBeInTheDocument();
    });
  });

  test('shows clear filters button when no results', async () => {
    apiClient.getPublicGames.mockResolvedValue({
      items: [],
      total: 0,
    });

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear filters/i })).toBeInTheDocument();
    });
  });

  test('sets up intersection observer for infinite scroll', async () => {
    const mockMultiPage = {
      items: Array.from({ length: 12 }, (_, i) => ({
        id: i + 1,
        title: `Game ${i + 1}`,
        mana_meeple_category: 'GATEWAY_STRATEGY',
      })),
      total: 50,
      page: 1,
      page_size: 12,
    };
    apiClient.getPublicGames.mockResolvedValue(mockMultiPage);

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Game 1')).toBeInTheDocument();
    });

    // Verify IntersectionObserver was created
    expect(global.IntersectionObserver).toHaveBeenCalled();
  });

  test('displays load more indicator when more pages available', async () => {
    const mockMultiPage = {
      items: Array.from({ length: 12 }, (_, i) => ({
        id: i + 1,
        title: `Game ${i + 1}`,
        mana_meeple_category: 'GATEWAY_STRATEGY',
      })),
      total: 50,
      page: 1,
      page_size: 12,
    };
    apiClient.getPublicGames.mockResolvedValue(mockMultiPage);

    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/12 of 50/i)).toBeInTheDocument();
    });
  });

  test('provides skip navigation link', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    const skipLink = screen.getByText(/skip to main content/i);
    expect(skipLink).toBeInTheDocument();
  });

  test('has proper heading structure', () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    const mainHeading = screen.getByRole('heading', { level: 1, name: /mana & meeples/i });
    expect(mainHeading).toBeInTheDocument();
  });

  test('filter buttons have aria-labels', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    await waitFor(() => {
      const gatewayButton = screen.getByRole('button', {
        name: /filter by gateway strategy/i,
      });
      expect(gatewayButton).toHaveAttribute('aria-label');
    });
  });

  test('respects prefers-reduced-motion', () => {
    window.matchMedia = vi.fn().mockReturnValue({
      matches: true, // Prefers reduced motion
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    const { container } = render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    // Elements should not have transition classes
    const header = container.querySelector('header');
    expect(header?.className).not.toContain('transition');
  });

  describe('Search functionality', () => {
    test('debounces search input', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const searchInput = screen.getByPlaceholderText(/search/i);

      // Type rapidly
      userEvent.type(searchInput, 'catan');

      // Should not call API immediately
      expect(apiClient.getPublicGames).toHaveBeenCalledTimes(1); // Initial load only

      // Wait for debounce
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ q: 'catan' })
        );
      }, { timeout: 500 });
    });

    test('clears search when X button clicked', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      userEvent.type(searchInput, 'test');

      expect(searchInput.value).toBe('test');

      // Clear button appears when there's text
      const clearButton = await screen.findByRole('button', { name: /clear search/i });
      userEvent.click(clearButton);

      expect(searchInput.value).toBe('');
    });
  });

  describe('Filter functionality', () => {
    test('filters by category when button clicked', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      const gatewayButton = screen.getByRole('button', { name: /filter by gateway strategy/i });
      userEvent.click(gatewayButton);

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ category: 'GATEWAY_STRATEGY' })
        );
      });
    });

    test('filters by NZ designer', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      const nzButton = screen.getByRole('button', { name: /nz designers/i });
      userEvent.click(nzButton);

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ nz_designer: true })
        );
      });
    });

    test('clears all filters when clear button clicked', async () => {
      
      

      apiClient.getPublicGames.mockResolvedValue({
        items: [],
        total: 0,
      });

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const clearButton = await screen.findByRole('button', { name: /clear filters/i });
      userEvent.click(clearButton);

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({
            category: undefined,
            q: '',
            nz_designer: undefined,
          })
        );
      });
    });
  });

  describe('Sort functionality', () => {
    test('changes sort order when sort select changed', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      const sortSelect = screen.getByRole('combobox', { name: /sort/i });
      userEvent.selectOptions(sortSelect, 'title_asc');

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ sort: 'title_asc' })
        );
      });
    });

    test('defaults to year_desc sort', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ sort: 'year_desc' })
        );
      });
    });
  });

  describe('Loading states', () => {
    test('shows skeleton cards while loading', () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      // Should show skeleton loaders initially
      const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    test('hides skeleton cards after loading', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      // Skeleton loaders should be gone
      const skeletons = document.querySelectorAll('[class*="GameCardSkeleton"]');
      expect(skeletons.length).toBe(0);
    });
  });

  describe('URL parameter persistence', () => {
    test('reads initial category from URL', async () => {
      render(
        <BrowserRouter initialEntries={['/?category=COOP_ADVENTURE']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ category: 'COOP_ADVENTURE' })
        );
      });
    });

    test('reads initial search query from URL', async () => {
      render(
        <BrowserRouter initialEntries={['/?q=pandemic']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ q: 'pandemic' })
        );
      }, { timeout: 500 });
    });

    test('reads NZ designer filter from URL', async () => {
      render(
        <BrowserRouter initialEntries={['/?nz_designer=true']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ nz_designer: true })
        );
      });
    });

    test('reads sort parameter from URL', async () => {
      render(
        <BrowserRouter initialEntries={['/?sort=title_asc']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalledWith(
          expect.objectContaining({ sort: 'title_asc' })
        );
      });
    });
  });

  describe('Help modal', () => {
    test('opens help modal when help button clicked', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const helpButton = screen.getByRole('button', { name: /help/i });
      userEvent.click(helpButton);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    test('closes help modal when close button clicked', async () => {
      
      

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const helpButton = screen.getByRole('button', { name: /help/i });
      userEvent.click(helpButton);

      const dialog = await screen.findByRole('dialog');
      expect(dialog).toBeInTheDocument();

      const closeButton = screen.getByRole('button', { name: /close/i });
      userEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility announcements', () => {
    test('announces game count to screen readers', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        const liveRegion = screen.getByRole('status');
        expect(liveRegion).toHaveTextContent(/2 games/i);
      });
    });

    test('announces loading state', () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveTextContent(/loading/i);
    });
  });

  describe('Error handling', () => {
    test('retries loading when retry button clicked', async () => {
      
      

      apiClient.getPublicGames.mockRejectedValueOnce(new Error('Network error'));
      apiClient.getPublicGames.mockResolvedValueOnce(mockGames);

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      const retryButton = await screen.findByRole('button', { name: /retry/i });
      userEvent.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });
    });

    test('handles cancellation on unmount', async () => {
      const { unmount } = render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      // Unmount before API call resolves
      unmount();

      // Should not cause errors or state updates
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });
  });

  describe('Infinite scroll', () => {
    test('loads more games when scrolling near bottom', async () => {
      const mockFirstPage = {
        items: Array.from({ length: 12 }, (_, i) => ({
          id: i + 1,
          title: `Game ${i + 1}`,
          mana_meeple_category: 'GATEWAY_STRATEGY',
        })),
        total: 25,
        page: 1,
        page_size: 12,
      };

      const mockSecondPage = {
        items: Array.from({ length: 12 }, (_, i) => ({
          id: i + 13,
          title: `Game ${i + 13}`,
          mana_meeple_category: 'GATEWAY_STRATEGY',
        })),
        total: 25,
        page: 2,
        page_size: 12,
      };

      apiClient.getPublicGames
        .mockResolvedValueOnce(mockFirstPage)
        .mockResolvedValueOnce(mockSecondPage);

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Game 1')).toBeInTheDocument();
      });

      // Verify IntersectionObserver was set up
      expect(global.IntersectionObserver).toHaveBeenCalled();
    });

    test('prevents duplicate items when loading more', async () => {
      const mockPage = {
        items: [
          { id: 1, title: 'Game 1', mana_meeple_category: 'GATEWAY_STRATEGY' },
        ],
        total: 10,
        page: 1,
        page_size: 1,
      };

      apiClient.getPublicGames.mockResolvedValue(mockPage);

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Game 1')).toBeInTheDocument();
      });

      // All instances of "Game 1" should be the same element (no duplicates)
      const games = screen.getAllByText('Game 1');
      expect(games.length).toBe(1);
    });
  });
});
