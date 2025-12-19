import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
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
    image_url: 'https://example.com/pandemic.jpg',
  };

  const mockOnToggleExpand = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders game title', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
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
        <GameCardPublic game={minimalGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('Test Game')).toBeInTheDocument();
  });

  it('displays category badge when category is provided', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('Co-op & Adventure')).toBeInTheDocument();
  });

  it('displays expansion badge for expansion games', () => {
    const expansionGame = {
      ...mockGame,
      is_expansion: true,
      expansion_type: 'expansion',
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={expansionGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('EXPANSION')).toBeInTheDocument();
  });

  it('displays standalone badge for standalone expansions', () => {
    const standaloneGame = {
      ...mockGame,
      is_expansion: true,
      expansion_type: 'standalone',
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={standaloneGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('STANDALONE')).toBeInTheDocument();
  });

  it('formats player count correctly', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const playerCounts = screen.getAllByText('2-4');
    expect(playerCounts.length).toBeGreaterThan(0);
  });

  it('formats single player count correctly', () => {
    const singlePlayerGame = {
      ...mockGame,
      min_players: 1,
      max_players: 1,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={singlePlayerGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const playerCounts = screen.getAllByText('1');
    expect(playerCounts.length).toBeGreaterThan(0);
  });

  it('formats time range correctly', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const times = screen.getAllByText('45-60 min');
    expect(times.length).toBeGreaterThan(0);
  });

  it('toggles expanded state when clicked', () => {
    render(
      <RouterWrapper>
        <GameCardPublic
          game={mockGame}
          isExpanded={false}
          onToggleExpand={mockOnToggleExpand}
        />
      </RouterWrapper>
    );

    const expandButtons = screen.getAllByLabelText(/expand details/i);
    fireEvent.click(expandButtons[0]);

    expect(mockOnToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('displays NZ designer badge when nz_designer is true', () => {
    const nzGame = {
      ...mockGame,
      nz_designer: true,
    };

    render(
      <RouterWrapper>
        <GameCardPublic
          game={nzGame}
          isExpanded={true}
          onToggleExpand={mockOnToggleExpand}
        />
      </RouterWrapper>
    );

    expect(screen.getByText('New Zealand Designer')).toBeInTheDocument();
  });
});
