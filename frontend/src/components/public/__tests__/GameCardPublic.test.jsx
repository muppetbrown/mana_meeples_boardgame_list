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

  it('formats rating correctly', () => {
    const { container } = render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    const ratingElements = screen.getAllByText(/7\.6/);
    expect(ratingElements.length).toBeGreaterThan(0);
  });

  it('handles missing rating', () => {
    const gameNoRating = {
      ...mockGame,
      average_rating: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoRating} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    // Should not crash and render without rating
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('formats complexity correctly', () => {
    const { container } = render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    const complexityElements = screen.getAllByText(/2\.4/);
    expect(complexityElements.length).toBeGreaterThan(0);
  });

  it('handles missing complexity', () => {
    const gameNoComplexity = {
      ...mockGame,
      complexity: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoComplexity} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    // Should not crash and render without complexity
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('formats time with min only', () => {
    const gameMinTime = {
      ...mockGame,
      playtime_min: 30,
      playtime_max: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameMinTime} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const times = screen.getAllByText('30 min');
    expect(times.length).toBeGreaterThan(0);
  });

  it('formats time with max only', () => {
    const gameMaxTime = {
      ...mockGame,
      playtime_min: null,
      playtime_max: 90,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameMaxTime} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const times = screen.getAllByText('90 min');
    expect(times.length).toBeGreaterThan(0);
  });

  it('shows "Time varies" when no time data', () => {
    const gameNoTime = {
      ...mockGame,
      playtime_min: null,
      playtime_max: null,
      playing_time: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoTime} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const times = screen.getAllByText('Time varies');
    expect(times.length).toBeGreaterThan(0);
  });

  it('displays player count with expansion', () => {
    const expansionPlayersGame = {
      ...mockGame,
      min_players: 2,
      max_players: 4,
      has_player_expansion: true,
      players_max_with_expansions: 6,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={expansionPlayersGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    const playerCounts = screen.getAllByText('2-6*');
    expect(playerCounts.length).toBeGreaterThan(0);
  });

  it('handles missing player count', () => {
    const gameNoPlayers = {
      ...mockGame,
      min_players: null,
      max_players: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoPlayers} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    // Should not crash and render without player count
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('displays year when provided', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    expect(screen.getByText('2008')).toBeInTheDocument();
  });

  it('displays designers when provided', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded={true} />
      </RouterWrapper>
    );
    expect(screen.getByText('Matt Leacock')).toBeInTheDocument();
  });

  it('handles different category styles', () => {
    const categories = ['GATEWAY_STRATEGY', 'CORE_STRATEGY', 'KIDS_FAMILIES', 'PARTY_ICEBREAKERS'];

    categories.forEach(category => {
      const gameWithCategory = {
        ...mockGame,
        mana_meeple_category: category,
      };

      const { unmount } = render(
        <RouterWrapper>
          <GameCardPublic game={gameWithCategory} onToggleExpand={mockOnToggleExpand} />
        </RouterWrapper>
      );

      expect(screen.getByText(gameWithCategory.title)).toBeInTheDocument();
      unmount();
    });
  });

  it('renders link to game details', () => {
    const { container } = render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );

    const links = container.querySelectorAll(`a[href="/game/${mockGame.id}"]`);
    expect(links.length).toBeGreaterThan(0);
  });

  it('respects prefersReducedMotion', () => {
    const { container } = render(
      <RouterWrapper>
        <GameCardPublic
          game={mockGame}
          onToggleExpand={mockOnToggleExpand}
          prefersReducedMotion={true}
        />
      </RouterWrapper>
    );

    // Should not have transition classes
    const card = container.firstChild;
    expect(card?.className).not.toContain('transition');
  });
});
