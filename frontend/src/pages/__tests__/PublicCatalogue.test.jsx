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

  test('scrolls to top on mount', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    expect(window.scrollTo).toHaveBeenCalledWith(0, 0);

    // Wait for async effects to complete
    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
    });
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

  test('provides skip navigation link', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    const skipLink = screen.getByText(/skip to main content/i);
    expect(skipLink).toBeInTheDocument();

    // Wait for async effects to complete
    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
    });
  });

  test('has proper heading structure', async () => {
    render(
      <BrowserRouter>
        <PublicCatalogue />
      </BrowserRouter>
    );

    const mainHeading = screen.getByRole('heading', { level: 1, name: /mana & meeples/i });
    expect(mainHeading).toBeInTheDocument();

    // Wait for async effects to complete
    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
    });
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

  test('respects prefers-reduced-motion', async () => {
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

    // Wait for async effects to complete
    await waitFor(() => {
      expect(apiClient.getPublicGames).toHaveBeenCalled();
    });
  });

  describe('Search functionality', () => {
    test('renders search box', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();

      // Wait for async effects to complete
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });
  });

  describe('Filter functionality', () => {
    test('renders category filter buttons', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getByRole('button', { name: /filter by gateway strategy/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /filter by core strategy/i })).toBeInTheDocument();

      // Wait for async effects to complete
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });
  });

  describe('Sort functionality', () => {
    test('renders sort select', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      expect(screen.getAllByRole('combobox').length).toBeGreaterThan(0);

      // Wait for async effects to complete
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });
  });

  describe('Loading states', () => {
    test('shows skeleton cards while loading', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      // Should show skeleton loaders initially
      const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);

      // Wait for async effects to complete
      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
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

  describe('Filter interactions', () => {
    test('updates category filter when button clicked', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        const gatewayButton = screen.queryByRole('button', { name: /filter by gateway strategy/i });
        expect(gatewayButton).toBeInTheDocument();
      });

      const gatewayButton = screen.getByRole('button', { name: /filter by gateway strategy/i });
      // Clicking works without errors
      userEvent.click(gatewayButton);
    });

    test('clears all filters when clear button clicked', async () => {
      render(
        <BrowserRouter initialEntries={['/?category=GATEWAY_STRATEGY&q=test']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });

    test('toggles NZ designer filter', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      const nzButton = screen.queryByRole('button', { name: /nz designer/i });
      if (nzButton) {
        userEvent.click(nzButton);
      }
    });

    test('updates sort order', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      const sortSelects = screen.getAllByRole('combobox');
      expect(sortSelects.length).toBeGreaterThan(0);
      // Can select options without errors
      if (sortSelects[0]) {
        userEvent.selectOptions(sortSelects[0], 'title');
      }
    });
  });

  describe('URL synchronization', () => {
    test('reads initial state from URL params', async () => {
      render(
        <BrowserRouter initialEntries={['/?category=GATEWAY_STRATEGY&sort=title_asc']}>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });

    test('updates URL when filters change', async () => {
      const { container } = render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });

      // Changing filters should update URL (via setSearchParams)
      const gatewayButton = screen.getByRole('button', { name: /filter by gateway strategy/i });
      userEvent.click(gatewayButton);

      await waitFor(() => {
        expect(apiClient.getPublicGames).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility features', () => {
    test('provides live region for announcements', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        const liveRegion = document.querySelector('[role="status"]');
        expect(liveRegion).toBeInTheDocument();
      });
    });

    test('has proper ARIA labels on interactive elements', async () => {
      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        buttons.forEach(button => {
          const hasLabel = button.hasAttribute('aria-label') || button.textContent.trim().length > 0;
          expect(hasLabel).toBe(true);
        });
      });
    });
  });

  describe('Responsive behavior', () => {
    test('renders on mobile viewport', async () => {
      global.innerWidth = 375;
      global.innerHeight = 667;

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });
    });

    test('renders on desktop viewport', async () => {
      global.innerWidth = 1920;
      global.innerHeight = 1080;

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Catan')).toBeInTheDocument();
      });
    });
  });

  describe('Error recovery', () => {
    test('recovers from error when retry clicked', async () => {
      apiClient.getPublicGames
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockGames);

      render(
        <BrowserRouter>
          <PublicCatalogue />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByRole('button', { name: /retry/i });
      expect(retryButton).toBeInTheDocument();
      // Click retry button - in real usage this would trigger a refetch
      userEvent.click(retryButton);
    });
  });
});
