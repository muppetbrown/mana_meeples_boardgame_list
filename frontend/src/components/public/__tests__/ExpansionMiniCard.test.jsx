import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import ExpansionMiniCard from '../ExpansionMiniCard';

// Mock GameImage component
vi.mock('../../GameImage', () => ({
  default: ({ alt, className }) => (
    <div data-testid="game-image" className={className}>
      {alt}
    </div>
  ),
}));

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('ExpansionMiniCard', () => {
  const mockExpansion = {
    id: 1,
    title: 'Test Expansion',
    image_url: 'https://example.com/image.jpg',
    players_min: 2,
    players_max: 4,
    modifies_players_min: 2,
    modifies_players_max: 6,
    expansion_type: 'requires_base',
  };

  describe('basic rendering', () => {
    it('renders expansion title', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      expect(screen.getByText('Test Expansion')).toBeInTheDocument();
    });

    it('renders as a link to game details page', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/game/1');
    });

    it('renders GameImage component with correct props', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const image = screen.getByTestId('game-image');
      expect(image).toBeInTheDocument();
      expect(image).toHaveTextContent('Cover for Test Expansion');
    });
  });

  describe('null/invalid expansion handling', () => {
    it('returns null when expansion is null', () => {
      const { container } = renderWithRouter(<ExpansionMiniCard expansion={null} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null when expansion is undefined', () => {
      const { container } = renderWithRouter(<ExpansionMiniCard expansion={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('returns null when expansion has no id', () => {
      const invalidExpansion = { title: 'No ID Expansion' };
      const { container } = renderWithRouter(<ExpansionMiniCard expansion={invalidExpansion} />);
      expect(container.firstChild).toBeNull();
    });

    it('logs warning when expansion data is invalid', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      renderWithRouter(<ExpansionMiniCard expansion={null} />);
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'ExpansionMiniCard received invalid expansion data:',
        null
      );
      consoleWarnSpy.mockRestore();
    });
  });

  describe('player count modifications', () => {
    it('displays player count modification when modifies_players_max is present', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      expect(screen.getByText(/Expands to 2-6 players/)).toBeInTheDocument();
    });

    it('uses modifies_players_min when available', () => {
      const expansion = {
        ...mockExpansion,
        modifies_players_min: 3,
        modifies_players_max: 8,
      };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText(/Expands to 3-8 players/)).toBeInTheDocument();
    });

    it('falls back to players_min when modifies_players_min is missing', () => {
      const expansion = {
        ...mockExpansion,
        modifies_players_min: undefined,
        modifies_players_max: 8,
        players_min: 2,
      };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText(/Expands to 2-8 players/)).toBeInTheDocument();
    });

    it('shows ? when both modifies_players_min and players_min are missing', () => {
      const expansion = {
        ...mockExpansion,
        modifies_players_min: undefined,
        players_min: undefined,
        modifies_players_max: 8,
      };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText(/Expands to \?-8 players/)).toBeInTheDocument();
    });

    it('does not display player count when modifies_players_max is missing', () => {
      const expansion = {
        ...mockExpansion,
        modifies_players_max: undefined,
      };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.queryByText(/Expands to/)).not.toBeInTheDocument();
    });
  });

  describe('expansion type badges', () => {
    it('displays "Standalone" badge for standalone expansion', () => {
      const expansion = { ...mockExpansion, expansion_type: 'standalone' };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Standalone')).toBeInTheDocument();
      expect(screen.getByText('Standalone')).toHaveClass('bg-indigo-100', 'text-indigo-800');
    });

    it('displays "Standalone" badge for both type', () => {
      const expansion = { ...mockExpansion, expansion_type: 'both' };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Standalone')).toBeInTheDocument();
    });

    it('displays "Requires Base" badge for requires_base type', () => {
      const expansion = { ...mockExpansion, expansion_type: 'requires_base' };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Requires Base')).toBeInTheDocument();
      expect(screen.getByText('Requires Base')).toHaveClass('bg-purple-100', 'text-purple-800');
    });

    it('displays generic "Expansion" badge for unknown type', () => {
      const expansion = { ...mockExpansion, expansion_type: 'unknown_type' };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Expansion')).toBeInTheDocument();
      expect(screen.getByText('Expansion')).toHaveClass('bg-slate-100', 'text-slate-800');
    });

    it('displays generic "Expansion" badge when expansion_type is missing', () => {
      const expansion = { ...mockExpansion, expansion_type: undefined };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Expansion')).toBeInTheDocument();
    });
  });

  describe('fallback content', () => {
    it('displays "Untitled Expansion" when title is missing', () => {
      const expansion = { id: 1, title: undefined };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByText('Untitled Expansion')).toBeInTheDocument();
    });

    it('passes undefined image_url to GameImage when missing', () => {
      const expansion = { ...mockExpansion, image_url: undefined };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      expect(screen.getByTestId('game-image')).toBeInTheDocument();
    });
  });

  describe('styling and layout', () => {
    it('has hover effects on the link', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const link = screen.getByRole('link');
      expect(link).toHaveClass('hover:shadow-lg', 'hover:border-purple-300');
    });

    it('has proper focus styles for accessibility', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const link = screen.getByRole('link');
      expect(link).toHaveClass('focus:outline-none', 'focus:ring-4', 'focus:ring-purple-200');
    });

    it('applies rounded styling to card', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const link = screen.getByRole('link');
      expect(link).toHaveClass('rounded-xl');
    });
  });

  describe('accessibility', () => {
    it('link is keyboard accessible', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href');
    });

    it('has meaningful alt text for image', () => {
      renderWithRouter(<ExpansionMiniCard expansion={mockExpansion} />);
      const image = screen.getByTestId('game-image');
      expect(image).toHaveTextContent('Cover for Test Expansion');
    });

    it('alt text handles missing title gracefully', () => {
      const expansion = { id: 1, image_url: 'test.jpg', title: undefined };
      renderWithRouter(<ExpansionMiniCard expansion={expansion} />);
      const image = screen.getByTestId('game-image');
      expect(image).toHaveTextContent('Cover for expansion');
    });
  });
});
