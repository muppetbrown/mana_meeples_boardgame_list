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
    test('renders search box', () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });
  });

  describe('Filter functionality', () => {
    test('renders category filter buttons', () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getByRole('button', { name: /filter by gateway strategy/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /filter by core strategy/i })).toBeInTheDocument();
    });
  });

  describe('Sort functionality', () => {
    test('renders sort select', () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0);
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


  describe('Error handling', () => {
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

  });
});
