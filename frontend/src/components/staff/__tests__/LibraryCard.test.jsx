/**
 * LibraryCard tests - Game card display component for staff library view
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LibraryCard from '../LibraryCard';

// Mock GameImage component
vi.mock('../../GameImage', () => ({
  default: vi.fn(({ url, alt, fallbackClass }) => (
    <div data-testid="game-image" data-url={url} data-alt={alt} data-fallback-class={fallbackClass}>
      {url ? 'Image' : 'No Image'}
    </div>
  )),
}));

describe('LibraryCard', () => {
  const mockOnEditCategory = vi.fn();
  const mockOnDelete = vi.fn();

  const mockGame = {
    id: 1,
    title: 'Test Game',
    cloudinary_url: 'https://cloudinary.com/test.jpg',
    image_url: 'https://example.com/test.jpg',
    players_min: 2,
    players_max: 4,
    playtime_min: 30,
    playtime_max: 60,
    mana_meeple_category: 'GATEWAY_STRATEGY',
    is_expansion: false,
    base_game_id: null,
    expansion_type: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders game title', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('Test Game')).toBeInTheDocument();
    });

    test('renders game image with cloudinary URL', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const image = screen.getByTestId('game-image');
      expect(image).toHaveAttribute('data-url', 'https://cloudinary.com/test.jpg');
      expect(image).toHaveAttribute('data-alt', 'Test Game');
    });

    test('falls back to image_url when cloudinary_url is missing', () => {
      const gameWithoutCloudinary = { ...mockGame, cloudinary_url: null };

      render(
        <LibraryCard
          game={gameWithoutCloudinary}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const image = screen.getByTestId('game-image');
      expect(image).toHaveAttribute('data-url', 'https://example.com/test.jpg');
    });

    test('renders edit category button', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByRole('button', { name: 'Edit Category' })).toBeInTheDocument();
    });

    test('renders delete button', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    });
  });

  describe('Player Count Display', () => {
    test('displays player count range', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/2–4/)).toBeInTheDocument();
    });

    test('displays question marks when player count is missing', () => {
      const gameWithoutPlayers = { ...mockGame, players_min: null, players_max: null };

      render(
        <LibraryCard
          game={gameWithoutPlayers}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/\?–\?/)).toBeInTheDocument();
    });

    test('displays expansion player count extension', () => {
      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        modifies_players_min: 5,
        modifies_players_max: 6,
      };

      render(
        <LibraryCard
          game={expansionGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/extends to 5-6/)).toBeInTheDocument();
    });

    test('uses original min when modifies_players_min is missing', () => {
      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        modifies_players_min: null,
        modifies_players_max: 6,
        players_min: 2,
      };

      render(
        <LibraryCard
          game={expansionGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/extends to 2-6/)).toBeInTheDocument();
    });
  });

  describe('Playtime Display', () => {
    test('displays playtime range when min and max differ', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/30-60 mins/)).toBeInTheDocument();
    });

    test('displays single playtime when min equals max', () => {
      const gameWithSinglePlaytime = { ...mockGame, playtime_min: 45, playtime_max: 45 };

      render(
        <LibraryCard
          game={gameWithSinglePlaytime}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/45 mins/)).toBeInTheDocument();
      expect(screen.queryByText(/45-45/)).not.toBeInTheDocument();
    });

    test('displays question mark when playtime is missing', () => {
      const gameWithoutPlaytime = { ...mockGame, playtime_min: null, playtime_max: null };

      render(
        <LibraryCard
          game={gameWithoutPlaytime}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/\? mins/)).toBeInTheDocument();
    });

    test('displays only min playtime when max is missing', () => {
      const gameWithMinOnly = { ...mockGame, playtime_min: 30, playtime_max: null };

      render(
        <LibraryCard
          game={gameWithMinOnly}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/30 mins/)).toBeInTheDocument();
    });

    test('displays only max playtime when min is missing', () => {
      const gameWithMaxOnly = { ...mockGame, playtime_min: null, playtime_max: 60 };

      render(
        <LibraryCard
          game={gameWithMaxOnly}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/60 mins/)).toBeInTheDocument();
    });
  });

  describe('Category Display', () => {
    test('displays category label', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('Gateway Strategy')).toBeInTheDocument();
    });

    test('displays "Uncategorized" when category is missing', () => {
      const gameWithoutCategory = { ...mockGame, mana_meeple_category: null };

      render(
        <LibraryCard
          game={gameWithoutCategory}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('Uncategorized')).toBeInTheDocument();
    });
  });

  describe('Expansion Display', () => {
    test('does not show expansion badge for non-expansions', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.queryByText('EXPANSION')).not.toBeInTheDocument();
      expect(screen.queryByText('STANDALONE')).not.toBeInTheDocument();
    });

    test('shows EXPANSION badge for requires_base expansion', () => {
      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'requires_base',
      };

      render(
        <LibraryCard
          game={expansionGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('EXPANSION')).toBeInTheDocument();
    });

    test('shows STANDALONE badge for standalone expansion', () => {
      const standaloneExpansion = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'standalone',
      };

      render(
        <LibraryCard
          game={standaloneExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('STANDALONE')).toBeInTheDocument();
    });

    test('shows STANDALONE badge for both expansion type', () => {
      const bothExpansion = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'both',
      };

      render(
        <LibraryCard
          game={bothExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('STANDALONE')).toBeInTheDocument();
    });

    test('shows expansion indicator when has base_game_id', () => {
      const linkedExpansion = {
        ...mockGame,
        is_expansion: true,
        base_game_id: 2,
      };

      render(
        <LibraryCard
          game={linkedExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText(/• Expansion/)).toBeInTheDocument();
    });

    test('does not show expansion indicator without base_game_id', () => {
      const unlinkedExpansion = {
        ...mockGame,
        is_expansion: true,
        base_game_id: null,
      };

      render(
        <LibraryCard
          game={unlinkedExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.queryByText(/• Expansion/)).not.toBeInTheDocument();
    });

    test('defaults to requires_base when expansion_type is missing', () => {
      const expansionWithoutType = {
        ...mockGame,
        is_expansion: true,
        expansion_type: null,
      };

      render(
        <LibraryCard
          game={expansionWithoutType}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      expect(screen.getByText('EXPANSION')).toBeInTheDocument();
    });
  });

  describe('Button Interactions', () => {
    test('calls onEditCategory when edit button clicked', async () => {
      const user = userEvent.setup();

      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Edit Category' }));

      expect(mockOnEditCategory).toHaveBeenCalledTimes(1);
      expect(mockOnEditCategory).toHaveBeenCalledWith(mockGame);
    });

    test('calls onDelete when delete button clicked', async () => {
      const user = userEvent.setup();

      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Delete' }));

      expect(mockOnDelete).toHaveBeenCalledTimes(1);
      expect(mockOnDelete).toHaveBeenCalledWith(mockGame);
    });

    test('edit and delete buttons work independently', async () => {
      const user = userEvent.setup();

      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Edit Category' }));
      expect(mockOnEditCategory).toHaveBeenCalledTimes(1);
      expect(mockOnDelete).not.toHaveBeenCalled();

      await user.click(screen.getByRole('button', { name: 'Delete' }));
      expect(mockOnDelete).toHaveBeenCalledTimes(1);
      expect(mockOnEditCategory).toHaveBeenCalledTimes(1);
    });
  });

  describe('Badge Styling', () => {
    test('applies indigo styling for standalone expansion', () => {
      const standaloneExpansion = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'standalone',
      };

      const { container } = render(
        <LibraryCard
          game={standaloneExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const badge = screen.getByText('STANDALONE');
      expect(badge).toHaveClass('bg-indigo-100');
      expect(badge).toHaveClass('text-indigo-800');
    });

    test('applies purple styling for requires_base expansion', () => {
      const requiresBaseExpansion = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'requires_base',
      };

      const { container } = render(
        <LibraryCard
          game={requiresBaseExpansion}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const badge = screen.getByText('EXPANSION');
      expect(badge).toHaveClass('bg-purple-100');
      expect(badge).toHaveClass('text-purple-800');
    });
  });

  describe('Accessibility', () => {
    test('buttons are keyboard accessible', async () => {
      const user = userEvent.setup();

      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const editButton = screen.getByRole('button', { name: 'Edit Category' });
      editButton.focus();
      expect(editButton).toHaveFocus();

      await user.keyboard('{Enter}');
      expect(mockOnEditCategory).toHaveBeenCalled();
    });

    test('game image has alt text', () => {
      render(
        <LibraryCard
          game={mockGame}
          onEditCategory={mockOnEditCategory}
          onDelete={mockOnDelete}
        />
      );

      const image = screen.getByTestId('game-image');
      expect(image).toHaveAttribute('data-alt', 'Test Game');
    });
  });
});
