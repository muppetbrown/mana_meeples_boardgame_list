import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import GameCardPublic from '../GameCardPublic';

// Wrapper for components that need Router
const RouterWrapper = ({ children }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('GameCardPublic', () => {
  const mockGame = {
    id: 1,
    title: 'Pandemic',
    year: 2008,
    players_min: 2,
    players_max: 4,
    playtime_min: 45,
    playtime_max: 60,
    complexity: 2.43,
    average_rating: 7.6,
    mana_meeple_category: 'COOP_ADVENTURE',
    designers: ['Matt Leacock'],
    image: 'https://example.com/pandemic.jpg',
  };

  it('renders game title', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} />
      </RouterWrapper>
    );
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('displays player count range', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} />
      </RouterWrapper>
    );
    // Player count is usually displayed as "2-4"
    expect(screen.getByText(/2-4/)).toBeInTheDocument();
  });

  it('displays year when available', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} />
      </RouterWrapper>
    );
    expect(screen.getByText(/2008/)).toBeInTheDocument();
  });

  it('displays complexity rating when available', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} />
      </RouterWrapper>
    );
    // Complexity is typically shown with decimal
    expect(screen.getByText(/2\.4/)).toBeInTheDocument();
  });

  it('handles missing optional fields gracefully', () => {
    const minimalGame = {
      id: 2,
      title: 'Test Game',
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={minimalGame} />
      </RouterWrapper>
    );
    expect(screen.getByText('Test Game')).toBeInTheDocument();
  });

  it('links to game details page', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} />
      </RouterWrapper>
    );
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/games/1');
  });
});
