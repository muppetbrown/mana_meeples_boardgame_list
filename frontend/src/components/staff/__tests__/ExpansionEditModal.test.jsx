/**
 * ExpansionEditModal tests - Expansion details editing modal
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExpansionEditModal from '../ExpansionEditModal';

describe('ExpansionEditModal', () => {
  const mockOnSave = vi.fn();
  const mockOnClose = vi.fn();

  const mockGame = {
    id: 1,
    title: 'Test Expansion',
    year: 2020,
    is_expansion: false,
    expansion_type: null,
    base_game_id: null,
    modifies_players_min: null,
    modifies_players_max: null,
  };

  const mockLibrary = [
    { id: 1, title: 'Test Expansion', is_expansion: false },
    { id: 2, title: 'Base Game 1', year: 2019, is_expansion: false },
    { id: 3, title: 'Base Game 2', year: 2021, is_expansion: false },
    { id: 4, title: 'Another Expansion', is_expansion: true },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders modal with title', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Edit Expansion Details')).toBeInTheDocument();
      expect(screen.getByText('Test Expansion')).toBeInTheDocument();
    });

    test('renders is expansion checkbox', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText('This is an expansion')).toBeInTheDocument();
    });

    test('renders action buttons', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Save Changes' })).toBeInTheDocument();
    });

    test('does not render expansion fields initially when not an expansion', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByText('Expansion Type')).not.toBeInTheDocument();
      expect(screen.queryByText('Base Game (Optional)')).not.toBeInTheDocument();
    });

    test('returns null when game is not provided', () => {
      const { container } = render(
        <ExpansionEditModal
          game={null}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Expansion Checkbox Toggle', () => {
    test('shows expansion fields when checkbox is checked', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const checkbox = screen.getByLabelText('This is an expansion');
      await user.click(checkbox);

      expect(screen.getByText('Expansion Type')).toBeInTheDocument();
      expect(screen.getByText('Base Game (Optional)')).toBeInTheDocument();
      expect(screen.getByText('Modified Player Count (Optional)')).toBeInTheDocument();
    });

    test('hides expansion fields when checkbox is unchecked', async () => {
      const user = userEvent.setup();

      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'requires_base',
      };

      render(
        <ExpansionEditModal
          game={expansionGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Fields should be visible initially
      expect(screen.getByText('Expansion Type')).toBeInTheDocument();

      const checkbox = screen.getByLabelText('This is an expansion');
      await user.click(checkbox);

      // Fields should be hidden after unchecking
      await waitFor(() => {
        expect(screen.queryByText('Expansion Type')).not.toBeInTheDocument();
      });
    });
  });

  describe('Expansion Type Selection', () => {
    test('displays expansion type dropdown when is expansion', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      // Get all comboboxes - first is expansion type, second is base game
      const selects = screen.getAllByRole('combobox');
      expect(selects.length).toBeGreaterThanOrEqual(1);
      expect(selects[0]).toBeInTheDocument();
    });

    test('shows all expansion type options', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const selects = screen.getAllByRole('combobox');
      const typeSelect = selects[0]; // First select is expansion type
      expect(typeSelect).toHaveValue('requires_base');

      // Check expansion type options are present
      expect(screen.getByRole('option', { name: 'Requires Base Game' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Standalone (can be played alone)' })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Both (standalone OR with base game)' })).toBeInTheDocument();
    });

    test('shows correct hint for requires_base type', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      expect(screen.getByText('🔒 Will NOT appear in public catalogue')).toBeInTheDocument();
    });

    test('shows correct hint for standalone type', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const selects = screen.getAllByRole('combobox');
      const typeSelect = selects[0];
      await user.selectOptions(typeSelect, 'standalone');

      expect(screen.getByText('✅ Will appear in public catalogue')).toBeInTheDocument();
    });

    test('shows correct hint for both type', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const selects = screen.getAllByRole('combobox');
      const typeSelect = selects[0];
      await user.selectOptions(typeSelect, 'both');

      const hints = screen.getAllByText('✅ Will appear in public catalogue');
      expect(hints.length).toBeGreaterThan(0);
    });
  });

  describe('Base Game Selection', () => {
    test('displays base game dropdown when is expansion', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const selects = screen.getAllByRole('combobox');
      const baseGameSelect = selects[1]; // Second select is base game
      expect(baseGameSelect).toBeInTheDocument();
    });

    test('filters out current game from base game options', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      // Current game (Test Expansion) should not be in the options
      expect(screen.queryByRole('option', { name: /Test Expansion/ })).not.toBeInTheDocument();
    });

    test('filters out other expansions from base game options', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      // Another Expansion should not be in the options
      expect(screen.queryByRole('option', { name: /Another Expansion/ })).not.toBeInTheDocument();
    });

    test('includes valid base games in options', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      expect(screen.getByRole('option', { name: /Base Game 1 \(2019\)/ })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Base Game 2 \(2021\)/ })).toBeInTheDocument();
    });

    test('shows -- None -- option', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      expect(screen.getByRole('option', { name: '-- None --' })).toBeInTheDocument();
    });
  });

  describe('Player Count Modifications', () => {
    test('displays player count inputs when is expansion', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      expect(screen.getByPlaceholderText('Min')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Max')).toBeInTheDocument();
    });

    test('allows entering min player count', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const minInput = screen.getByPlaceholderText('Min');
      await user.type(minInput, '5');

      expect(minInput).toHaveValue(5);
    });

    test('allows entering max player count', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const maxInput = screen.getByPlaceholderText('Max');
      await user.type(maxInput, '6');

      expect(maxInput).toHaveValue(6);
    });

    test('shows helper text for player count', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      expect(screen.getByText(/If this expansion extends the player count/)).toBeInTheDocument();
    });
  });

  describe('Form Initialization', () => {
    test('initializes with game data when game is an expansion', () => {
      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'standalone',
        base_game_id: 2,
        modifies_players_min: 5,
        modifies_players_max: 6,
      };

      render(
        <ExpansionEditModal
          game={expansionGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText('This is an expansion')).toBeChecked();

      const selects = screen.getAllByRole('combobox');
      expect(selects[0]).toHaveValue('standalone'); // Expansion type
      expect(selects[1]).toHaveValue('2'); // Base game

      expect(screen.getByPlaceholderText('Min')).toHaveValue(5);
      expect(screen.getByPlaceholderText('Max')).toHaveValue(6);
    });

    test('initializes with default values when game is not an expansion', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByLabelText('This is an expansion')).not.toBeChecked();
    });
  });

  describe('Form Submission', () => {
    test('calls onSave with correct data when not an expansion', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      expect(mockOnSave).toHaveBeenCalledWith({
        is_expansion: false,
        expansion_type: null,
        base_game_id: null,
        modifies_players_min: null,
        modifies_players_max: null,
      });
    });

    test('calls onSave with expansion data', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Enable expansion
      await user.click(screen.getByLabelText('This is an expansion'));

      // Get selects - first is expansion type, second is base game
      const selects = screen.getAllByRole('combobox');
      const typeSelect = selects[0];
      const baseGameSelect = selects[1];

      // Select expansion type
      await user.selectOptions(typeSelect, 'standalone');

      // Select base game
      await user.selectOptions(baseGameSelect, '2');

      // Enter player counts
      await user.type(screen.getByPlaceholderText('Min'), '5');
      await user.type(screen.getByPlaceholderText('Max'), '6');

      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      expect(mockOnSave).toHaveBeenCalledWith({
        is_expansion: true,
        expansion_type: 'standalone',
        base_game_id: 2,
        modifies_players_min: 5,
        modifies_players_max: 6,
      });
    });

    test('converts empty base game to null', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      // Leave base game as "-- None --"
      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          base_game_id: null,
        })
      );
    });

    test('converts empty player counts to null', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      // Leave player counts empty
      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          modifies_players_min: null,
          modifies_players_max: null,
        })
      );
    });

    test('parses player counts as integers', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      await user.type(screen.getByPlaceholderText('Min'), '5');
      await user.type(screen.getByPlaceholderText('Max'), '6');

      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      const call = mockOnSave.mock.calls[0][0];
      expect(typeof call.modifies_players_min).toBe('number');
      expect(typeof call.modifies_players_max).toBe('number');
    });

    test('sets expansion_type to null when not an expansion', async () => {
      const user = userEvent.setup();

      const expansionGame = {
        ...mockGame,
        is_expansion: true,
        expansion_type: 'requires_base',
      };

      render(
        <ExpansionEditModal
          game={expansionGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Uncheck expansion
      await user.click(screen.getByLabelText('This is an expansion'));

      await user.click(screen.getByRole('button', { name: 'Save Changes' }));

      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          is_expansion: false,
          expansion_type: null,
        })
      );
    });
  });

  describe('Cancel Button', () => {
    test('calls onClose when cancel button clicked', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    test('does not call onSave when cancel clicked', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    test('checkbox has proper label association', () => {
      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const checkbox = screen.getByLabelText('This is an expansion');
      expect(checkbox).toHaveAttribute('id', 'is_expansion');
    });

    test('form submits on enter key in inputs', async () => {
      const user = userEvent.setup();

      render(
        <ExpansionEditModal
          game={mockGame}
          library={mockLibrary}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByLabelText('This is an expansion'));

      const minInput = screen.getByPlaceholderText('Min');
      await user.type(minInput, '5{Enter}');

      expect(mockOnSave).toHaveBeenCalled();
    });
  });
});
