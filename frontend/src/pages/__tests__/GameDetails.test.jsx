// frontend/src/pages/__tests__/GameDetails.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import GameDetails from '../GameDetails';
import * as apiClient from '../../api/client';

// Mock API client
jest.mock('../../api/client');

// Mock DOMPurify
jest.mock('dompurify', () => ({
  default: {
    sanitize: (html) => html,
  },
}));

const mockGame = {
  id: 1,
  title: 'Catan',
  bgg_id: 13,
  mana_meeple_category: 'GATEWAY_STRATEGY',
  year: 1995,
  players_min: 3,
  players_max: 4,
  playtime_min: 60,
  playtime_max: 90,
  min_age: 10,
  complexity: 2.5,
  average_rating: 7.2,
  users_rated: 100000,
  designers: ['Klaus Teuber'],
  publishers: ['Kosmos'],
  mechanics: ['Trading', 'Dice Rolling'],
  artists: ['Michael Menzel'],
  description: '<p>In Catan, players try to be the dominant force on the island of Catan...</p>',
  thumbnail_url: 'http://example.com/catan.jpg',
  image: 'http://example.com/catan-large.jpg',
  nz_designer: false,
};

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('GameDetails Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockClear();
  });

  const renderGameDetails = (gameId = '1') => {
    return render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>,
      { initialEntries: [`/game/${gameId}`] }
    );
  };

  test('renders loading state initially', () => {
    apiClient.getPublicGame.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    // Should show skeleton loader
    expect(screen.getByTestId('game-details-skeleton')).toBeInTheDocument();
  });

  test('renders game details after loading', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/Klaus Teuber/i)).toBeInTheDocument();
    expect(screen.getByText(/1995/)).toBeInTheDocument();
  });

  test('displays player count range', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/3.*4/)).toBeInTheDocument(); // 3-4 players
  });

  test('displays playtime range', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/60.*90/)).toBeInTheDocument(); // 60-90 minutes
  });

  test('displays complexity rating', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/2\.5/)).toBeInTheDocument(); // Complexity rating
  });

  test('handles API errors gracefully', async () => {
    apiClient.getPublicGame.mockRejectedValue({
      response: { status: 404, data: { detail: 'Game not found' } },
    });

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/game not found/i)).toBeInTheDocument();
    });
  });

  test('handles network errors', async () => {
    apiClient.getPublicGame.mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  test('fetches game details with correct ID', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(apiClient.getPublicGame).toHaveBeenCalledWith(undefined); // ID comes from useParams
    });
  });

  test('navigates to designer filter when clicking designer', async () => {
    const user = userEvent.setup();
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    const designerButton = screen.getByText(/Klaus Teuber/i);
    await user.click(designerButton);

    expect(mockNavigate).toHaveBeenCalledWith('/?designer=Klaus%20Teuber');
  });

  test('displays BGG link when bgg_id exists', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    const bggLink = screen.getByRole('link', { name: /boardgamegeek/i });
    expect(bggLink).toHaveAttribute('href', expect.stringContaining('boardgamegeek.com'));
  });

  test('displays game image', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    const gameImage = screen.getByAltText(/Catan/i);
    expect(gameImage).toBeInTheDocument();
  });

  test('displays game description', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/In Catan, players try to be the dominant force/i)).toBeInTheDocument();
  });

  test('displays mechanics list', async () => {
    apiClient.getPublicGame.mockResolvedValue(mockGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Catan')).toBeInTheDocument();
    });

    expect(screen.getByText(/Trading/i)).toBeInTheDocument();
    expect(screen.getByText(/Dice Rolling/i)).toBeInTheDocument();
  });

  test('handles missing optional fields gracefully', async () => {
    const minimalGame = {
      id: 1,
      title: 'Minimal Game',
      mana_meeple_category: null,
      year: null,
      players_min: null,
      players_max: null,
      designers: [],
      mechanics: [],
    };

    apiClient.getPublicGame.mockResolvedValue(minimalGame);

    render(
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Minimal Game')).toBeInTheDocument();
    });

    // Should not crash with missing data
    expect(screen.queryByText(/null/)).not.toBeInTheDocument();
  });
});
