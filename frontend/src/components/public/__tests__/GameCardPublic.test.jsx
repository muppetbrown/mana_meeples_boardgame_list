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
    players_min: 2,
    players_max: 4,
    playtime_min: 45,
    playtime_max: 60,
    complexity: 2.43,
    average_rating: 7.6,
    mana_meeple_category: 'COOP_ADVENTURE',
    designers: ['Matt Leacock'],
    description: 'Work together to stop four diseases.',
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

  it('formats player count correctly', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('2-4')).toBeInTheDocument();
  });

  it('formats single player count correctly', () => {
    const singlePlayerGame = {
      ...mockGame,
      players_min: 1,
      players_max: 1,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={singlePlayerGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('formats time range correctly', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('45-60 min')).toBeInTheDocument();
  });

  it('shows a rules-crunch bucket derived from complexity', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    // complexity 2.43 falls in the Medium bucket (2.2 <= c < 3)
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('toggles expanded state when the expand button is clicked', () => {
    render(
      <RouterWrapper>
        <GameCardPublic
          game={mockGame}
          isExpanded={false}
          onToggleExpand={mockOnToggleExpand}
        />
      </RouterWrapper>
    );

    fireEvent.click(screen.getByLabelText('More info'));

    expect(mockOnToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('shows "Show less" and expanded details when isExpanded is true', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} isExpanded onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );

    expect(screen.getByLabelText('Show less')).toBeInTheDocument();
    expect(screen.getByText(mockGame.description)).toBeInTheDocument();
    expect(screen.getByText('View full details')).toBeInTheDocument();
  });

  it('formats rating correctly when expanded', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded />
      </RouterWrapper>
    );
    expect(screen.getByText(/7\.6/)).toBeInTheDocument();
  });

  it('handles missing rating without crashing', () => {
    const gameNoRating = {
      ...mockGame,
      average_rating: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoRating} onToggleExpand={mockOnToggleExpand} isExpanded />
      </RouterWrapper>
    );
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
    expect(screen.queryByText(/BGG rating/)).not.toBeInTheDocument();
  });

  it('formats complexity correctly when expanded', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded />
      </RouterWrapper>
    );
    expect(screen.getByText(/2\.4 \/ 5 · Medium/)).toBeInTheDocument();
  });

  it('handles missing complexity without crashing', () => {
    const gameNoComplexity = {
      ...mockGame,
      complexity: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoComplexity} onToggleExpand={mockOnToggleExpand} isExpanded />
      </RouterWrapper>
    );
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
    // Rules row falls back to an em dash when there's no complexity data
    expect(screen.getByText('—')).toBeInTheDocument();
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
    expect(screen.getByText('30 min')).toBeInTheDocument();
  });

  it('displays player count with expansion asterisk', () => {
    const expansionPlayersGame = {
      ...mockGame,
      players_min: 2,
      players_max: 4,
      has_player_expansion: true,
      players_max_with_expansions: 6,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={expansionPlayersGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('2-6*')).toBeInTheDocument();
  });

  it('handles missing player count without crashing', () => {
    const gameNoPlayers = {
      ...mockGame,
      players_min: null,
      players_max: null,
    };

    render(
      <RouterWrapper>
        <GameCardPublic game={gameNoPlayers} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByText('Pandemic')).toBeInTheDocument();
  });

  it('displays year and designers when expanded', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} isExpanded />
      </RouterWrapper>
    );
    expect(screen.getByText('2008')).toBeInTheDocument();
    expect(screen.getByText('Matt Leacock')).toBeInTheDocument();
  });

  it('renders links to the game details page', () => {
    const { container } = render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );

    const links = container.querySelectorAll(`a[href="/game/${mockGame.id}"]`);
    expect(links.length).toBeGreaterThan(0);
  });

  it('renders an Aftergame link', () => {
    render(
      <RouterWrapper>
        <GameCardPublic game={mockGame} onToggleExpand={mockOnToggleExpand} />
      </RouterWrapper>
    );
    expect(screen.getByLabelText('Organise a session on Aftergame')).toBeInTheDocument();
  });
});
