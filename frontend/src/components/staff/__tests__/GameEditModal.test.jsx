/**
 * Tests for GameEditModal component - unified modal for editing game properties
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import GameEditModal from '../GameEditModal';


// Mock SleevesListTable component
vi.mock('../SleevesListTable', () => ({
  default: ({ gameId }) => (
    <div data-testid="sleeves-list-table">SleevesListTable for game {gameId}</div>
  ),
}));


describe('GameEditModal', () => {
  let defaultProps;
  let mockOnSave;
  let mockOnClose;

  const mockGame = {
    id: 1,
    title: 'Pandemic',
    mana_meeple_category: 'COOP_ADVENTURE',
    is_expansion: false,
    expansion_type: null,
    base_game_id: null,
    modifies_players_min: null,
    modifies_players_max: null,
    aftergame_game_id: null,
  };

  const mockLibrary = [
    { id: 1, title: 'Pandemic', year: 2008, is_expansion: false },
    { id: 2, title: 'Catan', year: 1995, is_expansion: false },
    { id: 3, title: 'Ticket to Ride', year: 2004, is_expansion: false },
    { id: 4, title: 'Pandemic: On the Brink', year: 2009, is_expansion: true },
  ];

  beforeEach(() => {
    mockOnSave = vi.fn();
    mockOnClose = vi.fn();
    defaultProps = {
      game: mockGame,
      library: mockLibrary,
      onSave: mockOnSave,
      onClose: mockOnClose,
    };
  });

  describe('Rendering', () => {
    test('renders modal with game title', () => {
      render(<GameEditModal {...defaultProps} />);
      expect(screen.getByText('Edit Game')).toBeInTheDocument();
      expect(screen.getByText('Pandemic')).toBeInTheDocument();
    });

    test('renders null when game is null', () => {
      const { container } = render(<GameEditModal {...defaultProps} game={null} />);
      expect(container.firstChild).toBeNull();
    });

    test('renders all four tab buttons', () => {
      render(<GameEditModal {...defaultProps} />);
      expect(screen.getByText(/Category/)).toBeInTheDocument();
      expect(screen.getByText(/Expansion/)).toBeInTheDocument();
      expect(screen.getByText(/Sleeves/)).toBeInTheDocument();
      expect(screen.getByText(/AfterGame/)).toBeInTheDocument();
    });

    test('renders Cancel and Save buttons', () => {
      render(<GameEditModal {...defaultProps} />);
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Save Changes/i })).toBeInTheDocument();
    });
  });

  describe('Tab Navigation', () => {
    test('Category tab is active by default', () => {
      render(<GameEditModal {...defaultProps} />);
      expect(screen.getByText('Assign Category')).toBeInTheDocument();
    });

    test('clicking Expansion tab shows expansion content', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      expect(screen.getByText('This is an expansion')).toBeInTheDocument();
    });

    test('clicking Sleeves tab shows sleeves content', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Sleeves/));
      expect(screen.getByTestId('sleeves-list-table')).toBeInTheDocument();
    });

    test('clicking AfterGame tab shows integration content', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      expect(screen.getByText(/AfterGame Integration/)).toBeInTheDocument();
    });

    test('active tab has visual distinction', () => {
      render(<GameEditModal {...defaultProps} />);
      const categoryTab = screen.getByText(/Category/).closest('button');
      expect(categoryTab).toHaveClass('text-purple-600');
    });
  });

  describe('Category Tab', () => {
    test('renders all 5 category options plus uncategorized', () => {
      render(<GameEditModal {...defaultProps} />);
      expect(screen.getByText('Co-op & Adventure')).toBeInTheDocument();
      expect(screen.getByText('Core Strategy & Epics')).toBeInTheDocument();
      expect(screen.getByText('Gateway Strategy')).toBeInTheDocument();
      expect(screen.getByText('Kids & Families')).toBeInTheDocument();
      expect(screen.getByText('Party & Icebreakers')).toBeInTheDocument();
      expect(screen.getByText('Uncategorized')).toBeInTheDocument();
    });

    test('existing category is pre-selected', () => {
      render(<GameEditModal {...defaultProps} />);
      const coopRadio = screen.getByRole('radio', { name: /Co-op & Adventure/i });
      expect(coopRadio).toBeChecked();
    });

    test('can change category selection', () => {
      render(<GameEditModal {...defaultProps} />);
      const coreStrategyRadio = screen.getByRole('radio', { name: /Core Strategy & Epics/i });
      fireEvent.click(coreStrategyRadio);
      expect(coreStrategyRadio).toBeChecked();
    });

    test('can select uncategorized', () => {
      render(<GameEditModal {...defaultProps} />);
      const uncategorizedRadio = screen.getByRole('radio', { name: /Uncategorized/i });
      fireEvent.click(uncategorizedRadio);
      expect(uncategorizedRadio).toBeChecked();
    });
  });

  describe('Expansion Tab', () => {
    test('expansion checkbox is unchecked by default for non-expansion', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      expect(checkbox).not.toBeChecked();
    });

    test('checking expansion reveals additional fields', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      expect(screen.getByText('Expansion Type')).toBeInTheDocument();
      expect(screen.getByText('Base Game (Optional)')).toBeInTheDocument();
      expect(screen.getByText('Modified Player Count (Optional)')).toBeInTheDocument();
    });

    test('expansion type dropdown has three options', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      const select = screen.getByRole('combobox', { name: '' });
      expect(select.querySelector('option[value="requires_base"]')).toBeInTheDocument();
      expect(select.querySelector('option[value="standalone"]')).toBeInTheDocument();
      expect(select.querySelector('option[value="both"]')).toBeInTheDocument();
    });

    test('base game dropdown shows only non-expansions (excluding current game)', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      // Should show Catan and Ticket to Ride, but not Pandemic (current) or On the Brink (expansion)
      expect(screen.getByText(/Catan \(1995\)/)).toBeInTheDocument();
      expect(screen.getByText(/Ticket to Ride \(2004\)/)).toBeInTheDocument();
      expect(screen.queryByText(/Pandemic: On the Brink/)).not.toBeInTheDocument();
    });

    test('can enter player count modifications', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      const minInput = screen.getByPlaceholderText('Min');
      const maxInput = screen.getByPlaceholderText('Max');

      fireEvent.change(minInput, { target: { value: '5' } });
      fireEvent.change(maxInput, { target: { value: '6' } });

      expect(minInput).toHaveValue(5);
      expect(maxInput).toHaveValue(6);
    });

    test('shows visibility hint based on expansion type', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      // Default is requires_base
      expect(screen.getByText(/Will NOT appear in public catalogue/)).toBeInTheDocument();
    });
  });

  describe('Sleeves Tab', () => {
    test('renders SleevesListTable component', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Sleeves/));
      expect(screen.getByTestId('sleeves-list-table')).toBeInTheDocument();
    });

    test('passes game ID to SleevesListTable', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Sleeves/));
      expect(screen.getByText(/SleevesListTable for game 1/)).toBeInTheDocument();
    });

    test('shows shopping list note', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/Sleeves/));
      expect(screen.getByText(/shopping list will only include unmarked sleeve types/)).toBeInTheDocument();
    });
  });

  describe('AfterGame Integration Tab', () => {
    test('renders AfterGame integration info', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      expect(screen.getByText(/AfterGame Integration/)).toBeInTheDocument();
    });

    test('renders AfterGame ID input', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      expect(screen.getByPlaceholderText(/ac3a5f77-3e19-47af-a61a-d648d04b02e2/)).toBeInTheDocument();
    });

    test('shows amber warning when no AfterGame ID', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      expect(screen.getByText(/Without an AfterGame ID/)).toBeInTheDocument();
    });

    test('shows green success message when AfterGame ID is set', () => {
      const gameWithAftergame = {
        ...mockGame,
        aftergame_game_id: 'ac3a5f77-3e19-47af-a61a-d648d04b02e2',
      };
      render(<GameEditModal {...defaultProps} game={gameWithAftergame} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      expect(screen.getByText(/When set, the "Plan a Game" button/)).toBeInTheDocument();
    });

    test('can enter AfterGame ID', () => {
      render(<GameEditModal {...defaultProps} />);
      fireEvent.click(screen.getByText(/AfterGame/));
      const input = screen.getByPlaceholderText(/ac3a5f77-3e19-47af-a61a-d648d04b02e2/);
      fireEvent.change(input, { target: { value: 'test-uuid-value' } });
      expect(input).toHaveValue('test-uuid-value');
    });
  });

  describe('Form Submission', () => {
    test('calls onSave with correct data when Save clicked', async () => {
      render(<GameEditModal {...defaultProps} />);

      // Change category
      const coreStrategyRadio = screen.getByRole('radio', { name: /Core Strategy & Epics/i });
      fireEvent.click(coreStrategyRadio);

      // Submit form
      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith({
          mana_meeple_category: 'CORE_STRATEGY',
          is_expansion: false,
          expansion_type: null,
          base_game_id: null,
          modifies_players_min: null,
          modifies_players_max: null,
          aftergame_game_id: null,
        });
      });
    });

    test('calls onSave with expansion data when expansion is set', async () => {
      render(<GameEditModal {...defaultProps} />);

      // Switch to expansion tab
      fireEvent.click(screen.getByText(/Expansion/));

      // Check expansion checkbox
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      // Submit form
      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            is_expansion: true,
            expansion_type: 'requires_base',
          })
        );
      });
    });

    test('calls onSave with null category when uncategorized selected', async () => {
      render(<GameEditModal {...defaultProps} />);

      const uncategorizedRadio = screen.getByRole('radio', { name: /Uncategorized/i });
      fireEvent.click(uncategorizedRadio);

      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            mana_meeple_category: null,
          })
        );
      });
    });

    test('parses player count inputs as integers', async () => {
      render(<GameEditModal {...defaultProps} />);

      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      const minInput = screen.getByPlaceholderText('Min');
      const maxInput = screen.getByPlaceholderText('Max');
      fireEvent.change(minInput, { target: { value: '5' } });
      fireEvent.change(maxInput, { target: { value: '6' } });

      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            modifies_players_min: 5,
            modifies_players_max: 6,
          })
        );
      });
    });
  });

  describe('Modal Controls', () => {
    test('calls onClose when Cancel clicked', () => {
      render(<GameEditModal {...defaultProps} />);
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('modal has proper overlay styling', () => {
      const { container } = render(<GameEditModal {...defaultProps} />);
      const overlay = container.firstChild;
      expect(overlay).toHaveClass('fixed', 'inset-0', 'bg-black', 'bg-opacity-50');
    });
  });

  describe('Pre-population', () => {
    test('pre-populates expansion data from game', () => {
      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'standalone',
        base_game_id: 2,
        modifies_players_min: 5,
        modifies_players_max: 6,
      };
      render(<GameEditModal {...defaultProps} game={expansionGame} />);

      fireEvent.click(screen.getByText(/Expansion/));

      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      expect(checkbox).toBeChecked();
    });

    test('pre-populates aftergame_game_id from game', () => {
      const gameWithAftergame = {
        ...mockGame,
        aftergame_game_id: 'test-uuid-123',
      };
      render(<GameEditModal {...defaultProps} game={gameWithAftergame} />);

      fireEvent.click(screen.getByText(/AfterGame/));

      const input = screen.getByPlaceholderText(/ac3a5f77-3e19-47af-a61a-d648d04b02e2/);
      expect(input).toHaveValue('test-uuid-123');
    });
  });

  describe('Edge Cases', () => {
    test('handles game with no category set', () => {
      const uncategorizedGame = { ...mockGame, mana_meeple_category: null };
      render(<GameEditModal {...defaultProps} game={uncategorizedGame} />);

      const uncategorizedRadio = screen.getByRole('radio', { name: /Uncategorized/i });
      expect(uncategorizedRadio).toBeChecked();
    });

    test('handles empty library gracefully', () => {
      render(<GameEditModal {...defaultProps} library={[]} />);
      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      // Base game dropdown should only have "None" option
      expect(screen.getByText('-- None --')).toBeInTheDocument();
    });

    test('handles game without year in library', () => {
      const libraryWithoutYear = [
        { id: 2, title: 'Mystery Game', year: null, is_expansion: false },
      ];
      render(<GameEditModal {...defaultProps} library={libraryWithoutYear} />);

      fireEvent.click(screen.getByText(/Expansion/));
      const checkbox = screen.getByRole('checkbox', { name: /This is an expansion/i });
      fireEvent.click(checkbox);

      // Should show title without year
      expect(screen.getByText('Mystery Game')).toBeInTheDocument();
    });
  });
});
