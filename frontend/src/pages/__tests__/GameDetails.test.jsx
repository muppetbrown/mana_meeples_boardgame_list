// frontend/src/pages/__tests__/GameDetails.test.jsx
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
      <BrowserRouter>
        <Routes>
          <Route path="/game/:id" element={<GameDetails />} />
        </Routes>
      </BrowserRouter>
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
});
