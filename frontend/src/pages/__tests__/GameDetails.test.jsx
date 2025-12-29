// frontend/src/pages/__tests__/GameDetails.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
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
  designers: ['Klaus Teuber'],
  mana_meeple_category: 'GATEWAY_STRATEGY',
};

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('GameDetails Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders game details after loading', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
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
    apiClient.getPublicGame.mockRejectedValue({
      response: { status: 404, data: { detail: 'Game not found' } },
    });

    render(
      <MemoryRouter initialEntries={['/game/999']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/game not found/i)).toBeInTheDocument();
    });
  });

  test('displays loading state initially', () => {
    apiClient.getPublicGame.mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('displays game year', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
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

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/3-4 players/i)).toBeInTheDocument();
    });
  });

  test('displays designers', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
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

    render(
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

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /back to catalogue/i })).toBeInTheDocument();
    });
  });

  test('displays complexity if available', async () => {
    const gameWithComplexity = {
      ...mockGame,
      complexity: 2.5,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithComplexity);

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/2.5/)).toBeInTheDocument();
    });
  });

  test('displays BGG link if bgg_id available', async () => {
    const gameWithBGG = {
      ...mockGame,
      bgg_id: 13,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithBGG);

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const bggLink = screen.getByRole('link', { name: /boardgamegeek/i });
      expect(bggLink).toHaveAttribute('href', 'https://boardgamegeek.com/boardgame/13');
    });
  });

  test('displays playtime if available', async () => {
    const gameWithPlaytime = {
      ...mockGame,
      playtime_min: 60,
      playtime_max: 90,
    };
    apiClient.getPublicGame.mockResolvedValue(gameWithPlaytime);

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/60-90 min/i)).toBeInTheDocument();
    });
  });

  test('handles missing optional fields gracefully', async () => {
    const minimalGame = {
      id: 1,
      title: 'Minimal Game',
    };
    apiClient.getPublicGame.mockResolvedValue(minimalGame);

    render(
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

    render(
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

    render(
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
    apiClient.getPublicGame.mockRejectedValue(new Error('Network error'));

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  test('displays NZ designer badge if applicable', async () => {
    const nzGame = {
      ...mockGame,
      nz_designer: true,
    };
    apiClient.getPublicGame.mockResolvedValue(nzGame);

    render(
      <MemoryRouter initialEntries={['/game/1']}>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/NZ Designer/i)).toBeInTheDocument();
    });
  });
});
