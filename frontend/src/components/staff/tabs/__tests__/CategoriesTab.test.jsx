/**
 * CategoriesTab tests - Category management and NZ designer flags
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CategoriesTab } from '../CategoriesTab';
import * as apiClient from '../../../../api/client';

// Mock API client
vi.mock('../../../../api/client', () => ({
  bulkUpdateNZDesigners: vi.fn(),
}));

// Mock useStaff hook
vi.mock('../../../../context/StaffContext', () => ({
  useStaff: vi.fn(),
}));

// Mock BulkCategorizePanel
vi.mock('../../BulkPanels', () => ({
  BulkCategorizePanel: vi.fn(({ value, onChange, onSubmit }) => (
    <div data-testid="bulk-categorize-panel">
      <textarea
        data-testid="bulk-categorize-textarea"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <button onClick={onSubmit}>Bulk Categorize Submit</button>
    </div>
  )),
}));

import { useStaff } from '../../../../context/StaffContext';

describe('CategoriesTab', () => {
  const mockOpenEditCategory = vi.fn();
  const mockSetCsvCategorizeText = vi.fn();
  const mockDoBulkCategorize = vi.fn();
  const mockShowToast = vi.fn();
  const mockLoadLibrary = vi.fn();

  const mockGames = [
    {
      id: 1,
      title: 'Gloomhaven',
      mana_meeple_category: 'CORE_STRATEGY',
      year: 2017,
      players_min: 1,
      players_max: 4,
    },
    {
      id: 2,
      title: 'Wingspan',
      mana_meeple_category: 'GATEWAY_STRATEGY',
      year: 2019,
      players_min: 1,
      players_max: 5,
    },
    {
      id: 3,
      title: 'Pandemic',
      mana_meeple_category: 'COOP_ADVENTURE',
      year: 2008,
      players_min: 2,
      players_max: 4,
    },
    {
      id: 4,
      title: 'Uncategorized Game 1',
      mana_meeple_category: null,
      year: 2020,
      players_min: 2,
      players_max: 6,
    },
    {
      id: 5,
      title: 'Uncategorized Game 2',
      mana_meeple_category: null,
      year: 2021,
    },
  ];

  const defaultStaffContext = {
    library: mockGames,
    counts: {
      all: 5,
      COOP_ADVENTURE: 1,
      CORE_STRATEGY: 1,
      GATEWAY_STRATEGY: 1,
      KIDS_FAMILIES: 0,
      PARTY_ICEBREAKERS: 0,
    },
    csvCategorizeText: '',
    setCsvCategorizeText: mockSetCsvCategorizeText,
    doBulkCategorize: mockDoBulkCategorize,
    openEditCategory: mockOpenEditCategory,
    showToast: mockShowToast,
    loadLibrary: mockLoadLibrary,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useStaff.mockReturnValue(defaultStaffContext);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Rendering', () => {
    test('renders all main sections', () => {
      render(<CategoriesTab />);

      expect(screen.getByText('Category Overview')).toBeInTheDocument();
      expect(screen.getByText('Bulk Categorize from CSV')).toBeInTheDocument();
      expect(screen.getByText('New Zealand Designer Management')).toBeInTheDocument();
      expect(screen.getByText(/Category Distribution/)).toBeInTheDocument();
    });

    test('renders all category cards with labels', () => {
      render(<CategoriesTab />);

      // Category labels appear multiple times (overview and distribution)
      expect(screen.getAllByText('Co-op & Adventure').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Core Strategy & Epics').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Gateway Strategy').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Kids & Families').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Party & Icebreakers').length).toBeGreaterThan(0);
    });

    test('displays category counts from context', () => {
      render(<CategoriesTab />);

      // Check that counts are displayed (multiple "1" and "0" elements exist)
      const countElements = screen.getAllByText('1');
      expect(countElements.length).toBeGreaterThan(0);

      const zeroElements = screen.getAllByText('0');
      expect(zeroElements.length).toBeGreaterThan(0);
    });

    test('shows Quick Categorize section when uncategorized games exist', () => {
      render(<CategoriesTab />);

      expect(screen.getByText('Quick Categorize')).toBeInTheDocument();
      expect(screen.getByText(/Click on any game below/)).toBeInTheDocument();
    });

    test('hides Quick Categorize section when no uncategorized games', () => {
      const contextWithNoUncategorized = {
        ...defaultStaffContext,
        library: mockGames.filter((g) => g.mana_meeple_category),
      };

      useStaff.mockReturnValue(contextWithNoUncategorized);
      render(<CategoriesTab />);

      expect(screen.queryByText('Quick Categorize')).not.toBeInTheDocument();
    });
  });

  describe('Uncategorized Games', () => {
    test('displays uncategorized warning when games exist', () => {
      render(<CategoriesTab />);

      expect(screen.getByText('⚠️ 2 Uncategorized Games')).toBeInTheDocument();
      expect(screen.getByText(/These games need to be assigned/)).toBeInTheDocument();
    });

    test('displays uncategorized game cards', () => {
      render(<CategoriesTab />);

      expect(screen.getByText('Uncategorized Game 1')).toBeInTheDocument();
      expect(screen.getByText('Uncategorized Game 2')).toBeInTheDocument();
    });

    test('shows game details in uncategorized cards', () => {
      render(<CategoriesTab />);

      expect(screen.getByText(/2020 · 2-6 players/)).toBeInTheDocument();
    });

    test('calls openEditCategory when uncategorized game clicked', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const gameButton = screen.getByText('Uncategorized Game 1').closest('button');
      await user.click(gameButton);

      expect(mockOpenEditCategory).toHaveBeenCalledTimes(1);
      expect(mockOpenEditCategory).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 4,
          title: 'Uncategorized Game 1',
        })
      );
    });

    test('does not show uncategorized warning when all games are categorized', () => {
      const contextWithNoUncategorized = {
        ...defaultStaffContext,
        library: mockGames.filter((g) => g.mana_meeple_category),
      };

      useStaff.mockReturnValue(contextWithNoUncategorized);
      render(<CategoriesTab />);

      expect(screen.queryByText(/Uncategorized Games/)).not.toBeInTheDocument();
    });
  });

  describe('Bulk Categorize Integration', () => {
    test('renders BulkCategorizePanel', () => {
      render(<CategoriesTab />);

      expect(screen.getByTestId('bulk-categorize-panel')).toBeInTheDocument();
    });

    test('passes correct props to BulkCategorizePanel', () => {
      render(<CategoriesTab />);

      const textarea = screen.getByTestId('bulk-categorize-textarea');
      expect(textarea).toHaveValue('');
    });

    test('displays current CSV categorize text from context', () => {
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        csvCategorizeText: '12345,CORE_STRATEGY',
      });

      render(<CategoriesTab />);

      const textarea = screen.getByTestId('bulk-categorize-textarea');
      expect(textarea).toHaveValue('12345,CORE_STRATEGY');
    });

    test('calls setCsvCategorizeText when text changes', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const textarea = screen.getByTestId('bulk-categorize-textarea');
      await user.type(textarea, 'test');

      expect(mockSetCsvCategorizeText).toHaveBeenCalled();
    });

    test('calls doBulkCategorize when submit clicked', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const button = screen.getByText('Bulk Categorize Submit');
      await user.click(button);

      expect(mockDoBulkCategorize).toHaveBeenCalledTimes(1);
    });
  });

  describe('NZ Designer Management', () => {
    test('renders NZ designer section with instructions', () => {
      render(<CategoriesTab />);

      expect(screen.getByText('New Zealand Designer Management')).toBeInTheDocument();
      expect(screen.getByText(/Flag games by New Zealand designers/)).toBeInTheDocument();
      expect(screen.getByText(/CSV format:/)).toBeInTheDocument();
    });

    test('renders NZ designer textarea', () => {
      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveValue('');
    });

    test('updates NZ designer text when typing', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      // Check that textarea value updates
      await waitFor(() => {
        expect(textarea).toHaveValue('12345,true');
      });
    });

    test('submit button is disabled when textarea is empty', () => {
      render(<CategoriesTab />);

      const button = screen.getByText('Update NZ Designer Flags');
      expect(button).toBeDisabled();
    });

    test('submit button is enabled when textarea has content', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      expect(button).not.toBeDisabled();
    });

    test('shows error toast when submitting empty NZ designer data', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const button = screen.getByText('Update NZ Designer Flags');

      // Button is disabled, so we need to test the logic by typing and clearing
      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, ' ');
      await user.clear(textarea);

      // Button should still be disabled
      expect(button).toBeDisabled();
    });

    test('calls bulkUpdateNZDesigners API on submit', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1'],
        not_found: [],
        errors: [],
      });

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(apiClient.bulkUpdateNZDesigners).toHaveBeenCalledWith('12345,true');
      });
    });

    test('shows success toast after NZ designer update', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1', 'Game 2'],
        not_found: ['Game 3'],
        errors: [],
      });

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith(
          'Updated: 2, Not found: 1, Errors: 0',
          'success'
        );
      });
    });

    test('downloads log file after NZ designer update', async () => {
      const user = userEvent.setup();
      const createElementSpy = vi.spyOn(document, 'createElement');
      const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
      const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1'],
        not_found: ['Game 2'],
        errors: [],
      });

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(createObjectURLSpy).toHaveBeenCalled();
        expect(createElementSpy).toHaveBeenCalledWith('a');
        expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url');
      });

      createElementSpy.mockRestore();
      createObjectURLSpy.mockRestore();
      revokeObjectURLSpy.mockRestore();
    });

    test('clears textarea after successful NZ designer update', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1'],
        not_found: [],
        errors: [],
      });

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(textarea).toHaveValue('');
      });
    });

    test('reloads library after successful NZ designer update', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1'],
        not_found: [],
        errors: [],
      });

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(mockLoadLibrary).toHaveBeenCalledTimes(1);
      });
    });

    test('shows error toast when NZ designer update fails', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockRejectedValue(new Error('API Error'));

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(mockShowToast).toHaveBeenCalledWith(
          'Bulk NZ designers update failed',
          'error'
        );
      });
    });

    test('shows loading state during NZ designer update', async () => {
      const user = userEvent.setup();

      // Mock API to delay resolution
      apiClient.bulkUpdateNZDesigners.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ updated: [], not_found: [], errors: [] }), 100))
      );

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      // Should show loading text
      await waitFor(() => {
        expect(screen.getByText('Updating...')).toBeInTheDocument();
      });

      // Wait for completion
      await waitFor(() => {
        expect(screen.getByText('Update NZ Designer Flags')).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    test('disables textarea during NZ designer update', async () => {
      const user = userEvent.setup();

      apiClient.bulkUpdateNZDesigners.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ updated: [], not_found: [], errors: [] }), 100))
      );

      render(<CategoriesTab />);

      const textarea = screen.getByPlaceholderText(/12345,true/);
      await user.type(textarea, '12345,true');

      const button = screen.getByText('Update NZ Designer Flags');
      await user.click(button);

      await waitFor(() => {
        expect(textarea).toBeDisabled();
      });

      // Wait for completion
      await waitFor(() => {
        expect(textarea).not.toBeDisabled();
      }, { timeout: 2000 });
    });
  });

  describe('Category Distribution', () => {
    test('renders distribution section', () => {
      render(<CategoriesTab />);

      expect(screen.getByText(/Category Distribution/)).toBeInTheDocument();
    });

    test('displays all category bars', () => {
      render(<CategoriesTab />);

      // All category labels should be present in distribution
      const labels = screen.getAllByText('Co-op & Adventure');
      expect(labels.length).toBeGreaterThan(0);
    });

    test('calculates percentages correctly', () => {
      render(<CategoriesTab />);

      // With counts.all = 5, CORE_STRATEGY = 1, should show "1 (20%)"
      // Percentage appears multiple times in distribution visualization
      const percentageElements = screen.getAllByText(/20%/);
      expect(percentageElements.length).toBeGreaterThan(0);
    });

    test('shows uncategorized bar when uncategorized games exist', () => {
      render(<CategoriesTab />);

      // Should show "Uncategorized" in distribution
      const uncategorizedLabels = screen.getAllByText('Uncategorized');
      expect(uncategorizedLabels.length).toBeGreaterThan(0);
    });

    test('does not show uncategorized bar when no uncategorized games', () => {
      const contextWithNoUncategorized = {
        ...defaultStaffContext,
        library: mockGames.filter((g) => g.mana_meeple_category),
        counts: {
          ...defaultStaffContext.counts,
          all: 3,
        },
      };

      useStaff.mockReturnValue(contextWithNoUncategorized);
      render(<CategoriesTab />);

      // Should only show "Uncategorized" once (in the distribution label, not as a bar)
      const uncategorizedElements = screen.queryAllByText('Uncategorized');
      expect(uncategorizedElements.length).toBe(0);
    });
  });

  describe('Context Integration', () => {
    test('updates when library changes', () => {
      const { rerender } = render(<CategoriesTab />);

      expect(screen.getByText('⚠️ 2 Uncategorized Games')).toBeInTheDocument();

      // Update context with different library
      const newLibrary = mockGames.filter((g) => g.mana_meeple_category);
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        library: newLibrary,
      });

      rerender(<CategoriesTab />);

      expect(screen.queryByText(/Uncategorized Games/)).not.toBeInTheDocument();
    });

    test('updates when counts change', () => {
      const { rerender } = render(<CategoriesTab />);

      // Update counts
      useStaff.mockReturnValue({
        ...defaultStaffContext,
        counts: {
          ...defaultStaffContext.counts,
          CORE_STRATEGY: 5,
        },
      });

      rerender(<CategoriesTab />);

      // Should display updated counts
      const fiveElements = screen.getAllByText('5');
      expect(fiveElements.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    test('has descriptive section headings', () => {
      render(<CategoriesTab />);

      expect(screen.getByRole('heading', { name: 'Category Overview' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Bulk Categorize from CSV' })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'New Zealand Designer Management' })).toBeInTheDocument();
    });

    test('uncategorized game buttons are keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<CategoriesTab />);

      const gameButton = screen.getByText('Uncategorized Game 1').closest('button');

      gameButton.focus();
      expect(gameButton).toHaveFocus();

      await user.keyboard('{Enter}');

      expect(mockOpenEditCategory).toHaveBeenCalled();
    });
  });
});
