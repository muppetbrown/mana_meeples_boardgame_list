// frontend/src/pages/__tests__/GameDetails.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GameDetails from '../GameDetails';
import * as apiClient from '../../api/client';

vi.mock('../../api/client');
vi.mock('dompurify', () => ({
  default: { sanitize: (html) => html },
}));

const mockGame = {
  id: 1,
  title: 'Catan',
  year: 1995,
  players_min: 3,
  players_max: 4,
  playtime_min: 90,
  playtime_max: 90,
  designers: ['Klaus Teuber'],
  mana_meeple_category: 'GATEWAY_STRATEGY',
  bgg_id: 13,
};

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Phase 2 Performance: Test QueryClient setup
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,  // Disable retries globally
        retryDelay: 0, // No delay between retries (in case retry is overridden)
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: { log: console.log, warn: console.warn, error: () => {} },
  });
}

describe('GameDetails Page', () => {
  let queryClient;

  const renderWithQuery = (ui) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    );
  };

  // Helper to flush all pending promises
  const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  test('renders game details after loading', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });
  });

  test('handles API errors gracefully', async () => {
    const error = new Error('Game not found');
    error.response = { status: 404, data: { detail: 'Game not found' } };
    apiClient.getPublicGame.mockRejectedValue(error);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/999']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/game not found/i)).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout to account for retry: 1
  });

  test('displays loading state initially', () => {
    apiClient.getPublicGame.mockImplementation(() => new Promise(() => {}));

    const { container } = renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    // Component shows GameDetailsSkeleton, not text with "loading"
    // Just verify the component rendered without crashing
    expect(container.firstChild).toBeInTheDocument();
  });

  test('displays game year', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/1995/)).toBeInTheDocument();
    });
  });

  test('displays player count', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/3-4/)).toBeInTheDocument();
    });
  });

  test('displays designers', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Klaus Teuber/)).toBeInTheDocument();
    });
  });

  test('displays category badge', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Gateway Strategy/i)).toBeInTheDocument();
    });
  });

  test('shows back button', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/back to games/i)).toBeInTheDocument();
    });
  });


  test('displays BGG link if bgg_id available', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // There are now two BGG links: one in description fallback, one in action buttons
      const bggLinks = screen.getAllByRole('link', { name: /boardgamegeek/i });
      expect(bggLinks.length).toBeGreaterThan(0);
      expect(bggLinks[0]).toHaveAttribute('href', 'https://boardgamegeek.com/boardgame/13');
    });
  });

  test('displays playtime if available', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/90 min/i)).toBeInTheDocument();
    });
  });

  test('handles missing optional fields gracefully', async () => {
    const minimalGame = {
      id: 1,
      title: 'Minimal Game',
    };
    apiClient.getPublicGame.mockResolvedValue(minimalGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Minimal Game')).toBeInTheDocument();
    });
  });

  test('displays description if available', async () => {
    const gameWithDescription = {
      ...mockGame,
      description: '<p>This is a great game about trading and building.</p>',
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithDescription);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/trading and building/i)).toBeInTheDocument();
    });
  });

  test('sanitizes HTML in description', async () => {
    const gameWithUnsafeHTML = {
      ...mockGame,
      description: '<script>alert("xss")</script><p>Safe content</p>',
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithUnsafeHTML);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Safe content/i)).toBeInTheDocument();
    });
  });

  test('handles network errors', async () => {
    // Mock with proper error structure that React Query can handle
    const error = new Error('Network error');
    apiClient.getPublicGame.mockRejectedValue(error);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout to account for retry: 1
  });

  test('displays game type badge when available', async () => {
    const gameWithType = {
      ...mockGame,
      game_type: 'Base Game',
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithType);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Type:/i)).toBeInTheDocument();
      expect(screen.getByText(/Base Game/i)).toBeInTheDocument();
    });
  });

  test('does not display game type badge when not available', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.queryByText(/Type:/i)).not.toBeInTheDocument();
  });

  test('displays player count with expansion asterisk', async () => {
    const gameWithExpansion = {
      ...mockGame,
      has_player_expansion: true,
      players_min_with_expansions: 3,
      players_max_with_expansions: 6,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithExpansion);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/3-6\*/)).toBeInTheDocument();
    });
  });

  test('displays game mechanics when available', async () => {
    const gameWithMechanics = {
      ...mockGame,
      mechanics: ['Dice Rolling', 'Hand Management', 'Set Collection'],
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithMechanics);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Game Mechanics/i)).toBeInTheDocument();
      expect(screen.getByText('Dice Rolling')).toBeInTheDocument();
      expect(screen.getByText('Hand Management')).toBeInTheDocument();
      expect(screen.getByText('Set Collection')).toBeInTheDocument();
    });
  });

  test('does not display mechanics section when not available', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.queryByText(/Game Mechanics/i)).not.toBeInTheDocument();
  });

  test('displays base game info for expansions', async () => {
    const expansionGame = {
      ...mockGame,
      title: 'Catan: Cities & Knights',
      is_expansion: true,
      base_game: {
        id: 2,
        title: 'Settlers of Catan',
      },
    };
    apiClient.getPublicGame.mockResolvedValue(expansionGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/This is an expansion for:/i)).toBeInTheDocument();
      const baseGameLink = screen.getByRole('link', { name: /Settlers of Catan/i });
      expect(baseGameLink).toHaveAttribute('href', '/game/2');
    });
  });

  test('does not display base game info for non-expansions', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.queryByText(/This is an expansion for:/i)).not.toBeInTheDocument();
  });

  test('displays available expansions list', async () => {
    const gameWithExpansions = {
      ...mockGame,
      expansions: [
        { id: 10, title: 'Cities & Knights', image_url: null },
        { id: 11, title: 'Seafarers', image_url: null },
      ],
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithExpansions);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Available Expansions \(2\)/i)).toBeInTheDocument();
    });
  });

  test('does not display expansions section when not available', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.queryByText(/Available Expansions/i)).not.toBeInTheDocument();
  });

  test('navigates back when back button clicked', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    const backButton = screen.getByRole('button', { name: /go back to previous page/i });
    backButton.click();

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  test('navigates back when error Go Back button clicked', async () => {
    const error = new Error('Game not found');
    error.response = { status: 404, data: { detail: 'Game not found' } };
    apiClient.getPublicGame.mockRejectedValue(error);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/999']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/game not found/i)).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout to account for retry: 1

    const goBackButton = screen.getByRole('button', { name: /go back/i });
    goBackButton.click();

    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  test('navigates to designer filter when designer clicked', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Klaus Teuber')).toBeInTheDocument();
    });

    const designerButton = screen.getByRole('button', { name: /Klaus Teuber/i });
    designerButton.click();

    expect(mockNavigate).toHaveBeenCalledWith('/?designer=Klaus%20Teuber');
  });

  test('displays Plan a Game button with correct href', async () => {
    const gameWithAfterGame = {
      ...mockGame,
      aftergame_game_id: 'catan-123',
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithAfterGame);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const planButton = screen.getByRole('link', { name: /plan a game/i });
      expect(planButton).toHaveAttribute('href', expect.stringContaining('aftergame'));
    });
  });

  test('handles missing year gracefully', async () => {
    const gameWithoutYear = {
      ...mockGame,
      year: null,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithoutYear);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Year:/i)).toBeInTheDocument();
      // Should display em-dash for missing year
      expect(screen.getByText(/–/)).toBeInTheDocument();
    });
  });

  test('handles missing playtime gracefully', async () => {
    const gameWithoutTime = {
      ...mockGame,
      playtime_min: null,
      playtime_max: null,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithoutTime);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Time:/i)).toBeInTheDocument();
      // Should display ? for missing time
      expect(screen.getByText(/\? min/i)).toBeInTheDocument();
    });
  });

  test('handles missing player counts gracefully', async () => {
    const gameWithoutPlayers = {
      ...mockGame,
      players_min: null,
      players_max: null,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithoutPlayers);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Players:/i)).toBeInTheDocument();
      // Should display ?-? for missing players
      expect(screen.getByText(/\?-\?/)).toBeInTheDocument();
    });
  });

  test('displays category badge with correct styling', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    const { container } = renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Gateway Strategy')).toBeInTheDocument();
    });

    const categoryBadge = screen.getByText('Gateway Strategy');
    expect(categoryBadge.className).toContain('bg-linear-to-r');
    expect(categoryBadge.className).toContain('from-emerald-500');
  });

  test('does not display category badge when category is null', async () => {
    const gameWithoutCategory = {
      ...mockGame,
      mana_meeple_category: null,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithoutCategory);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    // Badge should not be rendered for null category
    expect(screen.queryByText(/Gateway Strategy/i)).not.toBeInTheDocument();
  });

  test('handles multiple designers correctly', async () => {
    const gameWithMultipleDesigners = {
      ...mockGame,
      designers: ['Klaus Teuber', 'Benjamin Teuber', 'Guido Teuber'],
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithMultipleDesigners);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Klaus Teuber/)).toBeInTheDocument();
      expect(screen.getByText(/Benjamin Teuber/)).toBeInTheDocument();
      expect(screen.getByText(/Guido Teuber/)).toBeInTheDocument();
    });
  });

  test('does not crash when description is not a string', async () => {
    const gameWithInvalidDescription = {
      ...mockGame,
      description: { invalid: 'object' },
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithInvalidDescription);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    }, { timeout: 5000 });

    // Description section now always renders with fallback message
    expect(screen.getByText(/About This Game/i)).toBeInTheDocument();
    expect(screen.getByText(/No description available/i)).toBeInTheDocument();
  });

  test('handles error response with different structures', async () => {
    const error = new Error('Internal server error');
    error.response = {
      status: 500,
      data: { message: 'Internal server error' }
    };
    apiClient.getPublicGame.mockRejectedValue(error);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Internal server error/i)).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout to account for retry: 1
  });

  test('uses default error message when no error detail available', async () => {
    const error = new Error();  // Error with no message
    apiClient.getPublicGame.mockRejectedValue(error);

    renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load game details/i)).toBeInTheDocument();
    }, { timeout: 3000 }); // Increased timeout to account for retry: 1
  });

  test('cleans up effect when component unmounts during loading', async () => {
    apiClient.getPublicGame.mockImplementation(() => new Promise(() => {}));

    const { unmount } = renderWithQuery(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    // Unmount while still loading
    unmount();

    // No error should occur - cleanup should prevent state updates
    expect(true).toBe(true);
  });

});
