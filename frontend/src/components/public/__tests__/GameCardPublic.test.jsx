import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GameCardPublic from '../GameCardPublic';

// Wrapper for components that need Router
const RouterWrapper = ({ children }) => (
  <MemoryRouter>{children}</MemoryRouter>
);

describe('GameCardPublic', () => {
  const mockGame = {
    id: 1,
    title: 'Pandemic',
    year: 2008,
    min_players: 2,
    max_players: 4,
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
});
