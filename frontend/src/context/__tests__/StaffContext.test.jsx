/**
 * StaffContext tests - Comprehensive coverage for staff interface state management
 */
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StaffProvider, useStaff } from '../StaffContext';
import * as apiClient from '../../api/client';
import { mockGames, mockCategoryCounts } from '../../test/mockData';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock API client
vi.mock('../../api/client', () => ({
  validateAdminToken: vi.fn(),
  getGames: vi.fn(),
  bulkImportCsv: vi.fn(),
  bulkCategorizeCsv: vi.fn(),
  updateGame: vi.fn(),
  deleteGame: vi.fn(),
  importFromBGG: vi.fn(),
}));

// Test component that uses StaffContext
function TestComponent({ onContextValue }) {
  const context = useStaff();
  if (onContextValue) {
    onContextValue(context);
  }
  return (
    <div>
      <div data-testid="library-count">{context.library.length}</div>
      <div data-testid="selected-category">{context.selectedCategory}</div>
      <div data-testid="toast-message">{context.toast.message}</div>
      <div data-testid="is-validating">{context.isValidating.toString()}</div>
      <div data-testid="is-loading">{context.isLoading.toString()}</div>
      <div data-testid="stats-total">{context.stats.total}</div>
      <div data-testid="stats-rating">{context.stats.avgRating}</div>
    </div>
  );
}

describe('StaffProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default successful validation
    apiClient.validateAdminToken.mockResolvedValue({});
    apiClient.getGames.mockResolvedValue(mockGames);
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Initialization', () => {
    test('validates admin session on mount', async () => {
      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(apiClient.validateAdminToken).toHaveBeenCalledTimes(1);
      });
    });

    test('redirects to login if validation fails', async () => {
      apiClient.validateAdminToken.mockRejectedValue(new Error('Unauthorized'));

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/staff/login');
      });
    });

    test('loads library after successful validation', async () => {
      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(apiClient.getGames).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('library-count')).toHaveTextContent('5');
      });
    });

    test('initializes with correct default state', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      expect(contextValue.selectedCategory).toBe('all');
      expect(contextValue.csvImportText).toBe('');
      expect(contextValue.csvCategorizeText).toBe('');
      expect(contextValue.bggIdInput).toBe('');
      expect(contextValue.modalOpen).toBe(false);
      expect(contextValue.modalMode).toBe('add');
      expect(contextValue.pendingGame).toBeNull();
    });
  });

  describe('Library Management', () => {
    test('fetches and sets library data', async () => {
      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('library-count')).toHaveTextContent('5');
      });
    });

    test('computes stats correctly', async () => {
      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('stats-total')).toHaveTextContent('5');
        // Average of ratings: (8.67 + 8.07 + 7.60 + 7.68 + 7.42) / 5 = 7.888 ≈ 7.9
        expect(screen.getByTestId('stats-rating')).toHaveTextContent('7.9');
      });
    });

    test('computes category counts correctly', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      // Wait for library to be loaded
      await waitFor(() => {
        expect(contextValue?.counts?.all).toBe(5);
      });

      expect(contextValue.counts.CORE_STRATEGY).toBe(1); // Gloomhaven
      expect(contextValue.counts.GATEWAY_STRATEGY).toBe(1); // Wingspan
      expect(contextValue.counts.COOP_ADVENTURE).toBe(1); // Pandemic
      expect(contextValue.counts.PARTY_ICEBREAKERS).toBe(1); // Codenames
      expect(contextValue.counts.KIDS_FAMILIES).toBe(1); // Kingdomino
    });

    test('filters library by selected category', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      // Wait for library to load
      await waitFor(() => {
        expect(contextValue?.filteredLibrary?.length).toBe(5);
      });

      // Default: all games
      expect(contextValue.filteredLibrary.length).toBe(5);

      // Change to specific category
      act(() => {
        contextValue.setSelectedCategory('GATEWAY_STRATEGY');
      });

      await waitFor(() => {
        expect(contextValue.filteredLibrary.length).toBe(1);
        expect(contextValue.filteredLibrary[0].title).toBe('Wingspan');
      });
    });

    test('filters uncategorized games correctly', async () => {
      const gamesWithUncategorized = [
        ...mockGames,
        { id: 99, title: 'Uncategorized Game', mana_meeple_category: null, status: 'OWNED' },
      ];
      apiClient.getGames.mockResolvedValue(gamesWithUncategorized);

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue.counts.uncategorized).toBe(1);
      });

      act(() => {
        contextValue.setSelectedCategory('uncategorized');
      });

      await waitFor(() => {
        expect(contextValue.filteredLibrary.length).toBe(1);
        expect(contextValue.filteredLibrary[0].title).toBe('Uncategorized Game');
      });
    });

    test('handles empty library gracefully', async () => {
      apiClient.getGames.mockResolvedValue([]);

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('library-count')).toHaveTextContent('0');
        expect(screen.getByTestId('stats-total')).toHaveTextContent('0');
        expect(screen.getByTestId('stats-rating')).toHaveTextContent('N/A');
      });
    });

    test('reloads library on loadLibrary call', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(apiClient.getGames).toHaveBeenCalledTimes(1);
      });

      // Call loadLibrary again
      await act(async () => {
        await contextValue.loadLibrary();
      });

      expect(apiClient.getGames).toHaveBeenCalledTimes(2);
    });

    test('handles API error when loading library', async () => {
      apiClient.getGames.mockRejectedValue(new Error('API Error'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue.error).toBe('Failed to load library');
        expect(contextValue.library).toEqual([]);
      });
    });

    test('filters out non-OWNED games from display', async () => {
      const gamesWithStatuses = [
        ...mockGames,
        { id: 100, title: 'Wishlist Game', mana_meeple_category: 'GATEWAY_STRATEGY', status: 'WISHLIST' },
        { id: 101, title: 'Buy List Game', mana_meeple_category: 'GATEWAY_STRATEGY', status: 'BUY_LIST' },
      ];
      apiClient.getGames.mockResolvedValue(gamesWithStatuses);

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      // Wait for library to be loaded with correct count
      await waitFor(() => {
        expect(contextValue?.filteredLibrary?.length).toBe(5);
      });

      // Should only show OWNED games (or null status which defaults to OWNED)
      expect(contextValue.filteredLibrary.every(g => !g.status || g.status === 'OWNED')).toBe(true);
    });
  });

  describe('BGG Import with Retry Logic', () => {
    test('successfully imports game on first attempt', async () => {
      apiClient.importFromBGG.mockResolvedValue({ title: 'New Game' });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await act(async () => {
        await contextValue.addGameByBggId(12345);
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledWith(12345);
      expect(apiClient.importFromBGG).toHaveBeenCalledTimes(1);
      expect(apiClient.getGames).toHaveBeenCalledTimes(2); // Initial load + reload after import
    });

    test('retries on server error with exponential backoff', async () => {
      apiClient.importFromBGG
        .mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Server error' } } })
        .mockRejectedValueOnce({ response: { status: 503, data: { detail: 'Service unavailable' } } })
        .mockResolvedValueOnce({ title: 'New Game' });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      // Start import (will retry automatically)
      const importPromise = contextValue.addGameByBggId(12345);

      // Wait for retries to complete
      await act(async () => {
        await importPromise;
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledTimes(3); // Initial + 2 retries
    }, 15000); // Increase timeout to allow for retry delays

    test('does not retry on 4xx client errors', async () => {
      apiClient.importFromBGG.mockRejectedValue({
        response: { status: 404, data: { detail: 'Game not found' } },
      });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await act(async () => {
        await contextValue.addGameByBggId(99999);
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledTimes(1); // No retries
    });

    test('retries on 429 rate limiting', async () => {
      apiClient.importFromBGG
        .mockRejectedValueOnce({ response: { status: 429, data: { detail: 'Rate limit exceeded' } } })
        .mockResolvedValueOnce({ title: 'New Game' });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      const importPromise = contextValue.addGameByBggId(12345);

      await act(async () => {
        await importPromise;
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledTimes(2); // Initial + 1 retry
    }, 10000); // Increase timeout to allow for retry delay

    test('gives up after maximum retries', async () => {
      apiClient.importFromBGG.mockRejectedValue({
        response: { status: 500, data: { detail: 'Server error' } },
      });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      const importPromise = contextValue.addGameByBggId(12345);

      await act(async () => {
        await importPromise;
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledTimes(5); // Initial + 4 retries
    }, 40000); // Increase timeout to allow for all retry delays (2+4+8+16 = 30s + buffer)

    test('handleAddGame validates BGG ID input', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      // Test invalid inputs
      act(() => {
        contextValue.setBggIdInput('');
      });
      await act(async () => {
        contextValue.handleAddGame();
      });
      expect(apiClient.importFromBGG).not.toHaveBeenCalled();

      act(() => {
        contextValue.setBggIdInput('abc');
      });
      await act(async () => {
        contextValue.handleAddGame();
      });
      expect(apiClient.importFromBGG).not.toHaveBeenCalled();

      act(() => {
        contextValue.setBggIdInput('-5');
      });
      await act(async () => {
        contextValue.handleAddGame();
      });
      expect(apiClient.importFromBGG).not.toHaveBeenCalled();

      // Test valid input
      act(() => {
        contextValue.setBggIdInput('12345');
      });

      apiClient.importFromBGG.mockResolvedValue({ title: 'Valid Game' });

      const handlePromise = contextValue.handleAddGame();

      await act(async () => {
        await handlePromise;
      });

      expect(apiClient.importFromBGG).toHaveBeenCalledWith(12345);

      // Wait for state updates to complete
      await waitFor(() => {
        expect(contextValue.bggIdInput).toBe(''); // Should clear input after success
      });
    });
  });

  describe('Bulk Operations', () => {
    test('bulk import with valid CSV', async () => {
      apiClient.bulkImportCsv.mockResolvedValue({ success: true });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.setCsvImportText('174430\n266192\n30549');
      });

      await act(async () => {
        await contextValue.doBulkImport();
      });

      expect(apiClient.bulkImportCsv).toHaveBeenCalledWith('174430\n266192\n30549');
      expect(apiClient.getGames).toHaveBeenCalledTimes(2); // Initial + reload
      expect(contextValue.csvImportText).toBe(''); // Should clear after success
    });

    test('bulk import skips if CSV empty', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await act(async () => {
        await contextValue.doBulkImport();
      });

      expect(apiClient.bulkImportCsv).not.toHaveBeenCalled();
    });

    test('bulk import handles API error', async () => {
      apiClient.bulkImportCsv.mockRejectedValue(new Error('Import failed'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.setCsvImportText('174430');
      });

      await act(async () => {
        await contextValue.doBulkImport();
      });

      expect(apiClient.bulkImportCsv).toHaveBeenCalled();
      // CSV text should NOT be cleared on error
      expect(contextValue.csvImportText).toBe('174430');
    });

    test('bulk categorize with valid CSV', async () => {
      apiClient.bulkCategorizeCsv.mockResolvedValue({ success: true });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.setCsvCategorizeText('1,GATEWAY_STRATEGY\n2,CORE_STRATEGY');
      });

      await act(async () => {
        await contextValue.doBulkCategorize();
      });

      expect(apiClient.bulkCategorizeCsv).toHaveBeenCalledWith('1,GATEWAY_STRATEGY\n2,CORE_STRATEGY');
      expect(apiClient.getGames).toHaveBeenCalledTimes(2);
      expect(contextValue.csvCategorizeText).toBe('');
    });

    test('bulk categorize skips if CSV empty', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await act(async () => {
        await contextValue.doBulkCategorize();
      });

      expect(apiClient.bulkCategorizeCsv).not.toHaveBeenCalled();
    });

    test('bulk categorize handles API error', async () => {
      apiClient.bulkCategorizeCsv.mockRejectedValue(new Error('Categorize failed'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.setCsvCategorizeText('1,GATEWAY_STRATEGY');
      });

      await act(async () => {
        await contextValue.doBulkCategorize();
      });

      expect(contextValue.csvCategorizeText).toBe('1,GATEWAY_STRATEGY'); // Should NOT clear on error
    });
  });

  describe('Modal Management', () => {
    test('opens modal in edit mode', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      const testGame = mockGames[0];

      act(() => {
        contextValue.openEditCategory(testGame);
      });

      expect(contextValue.modalOpen).toBe(true);
      expect(contextValue.modalMode).toBe('edit');
      expect(contextValue.pendingGame).toBe(testGame);
    });

    test('closes modal and resets state', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      // Open modal first
      act(() => {
        contextValue.openEditCategory(mockGames[0]);
      });

      expect(contextValue.modalOpen).toBe(true);

      // Close modal
      act(() => {
        contextValue.handleModalClose();
      });

      expect(contextValue.modalOpen).toBe(false);
      expect(contextValue.pendingGame).toBeNull();
    });

    test('handles modal category selection in edit mode', async () => {
      apiClient.updateGame.mockResolvedValue({ success: true });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      // Open modal with a game
      act(() => {
        contextValue.openEditCategory(mockGames[0]);
      });

      // Select a category
      await act(async () => {
        await contextValue.handleModalSelect('GATEWAY_STRATEGY');
      });

      expect(apiClient.updateGame).toHaveBeenCalledWith(mockGames[0].id, {
        mana_meeple_category: 'GATEWAY_STRATEGY',
      });
      expect(contextValue.modalOpen).toBe(false);
      expect(contextValue.pendingGame).toBeNull();
    });

    test('handles modal selection error gracefully', async () => {
      apiClient.updateGame.mockRejectedValue(new Error('Update failed'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.openEditCategory(mockGames[0]);
      });

      await act(async () => {
        await contextValue.handleModalSelect('GATEWAY_STRATEGY');
      });

      // Modal should close even on error
      expect(contextValue.modalOpen).toBe(false);
      expect(contextValue.pendingGame).toBeNull();
    });
  });

  describe('Game CRUD Operations', () => {
    test('updates game successfully', async () => {
      apiClient.updateGame.mockResolvedValue({ success: true });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      const updates = { title: 'Updated Title', year: 2025 };

      await act(async () => {
        await contextValue.updateGameData(1, updates);
      });

      expect(apiClient.updateGame).toHaveBeenCalledWith(1, updates);
      expect(apiClient.getGames).toHaveBeenCalledTimes(2); // Initial + reload
    });

    test('update game throws error on failure', async () => {
      apiClient.updateGame.mockRejectedValue(new Error('Update failed'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await expect(
        act(async () => {
          await contextValue.updateGameData(1, { title: 'New Title' });
        })
      ).rejects.toThrow();
    });

    test('deletes game successfully', async () => {
      apiClient.deleteGame.mockResolvedValue({ success: true });

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await act(async () => {
        await contextValue.deleteGameData(1);
      });

      expect(apiClient.deleteGame).toHaveBeenCalledWith(1);
      expect(apiClient.getGames).toHaveBeenCalledTimes(2);
    });

    test('delete game throws error on failure', async () => {
      apiClient.deleteGame.mockRejectedValue(new Error('Delete failed'));

      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      await expect(
        act(async () => {
          await contextValue.deleteGameData(1);
        })
      ).rejects.toThrow();
    });
  });

  describe('Toast Notifications', () => {
    test('shows toast with custom message', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.showToast('Test message', 'success');
      });

      expect(contextValue.toast.message).toBe('Test message');
      expect(contextValue.toast.type).toBe('success');
    });

    test('auto-dismisses toast after timeout', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      act(() => {
        contextValue.showToast('Test message', 'info', 100); // Use short timeout for test
      });

      expect(contextValue.toast.message).toBe('Test message');

      // Wait for toast to auto-dismiss
      await waitFor(() => {
        expect(contextValue.toast.message).toBe('');
      }, { timeout: 2000 });
    });

    test('handles different toast types', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
      });

      // Test success toast
      act(() => {
        contextValue.showToast('Success', 'success');
      });
      expect(contextValue.toast.type).toBe('success');

      // Test error toast
      act(() => {
        contextValue.showToast('Error', 'error');
      });
      expect(contextValue.toast.type).toBe('error');

      // Test warning toast
      act(() => {
        contextValue.showToast('Warning', 'warning');
      });
      expect(contextValue.toast.type).toBe('warning');

      // Test info toast (default)
      act(() => {
        contextValue.showToast('Info');
      });
      expect(contextValue.toast.type).toBe('info');
    });
  });

  describe('useStaff Hook', () => {
    test('throws error when used outside provider', () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = vi.fn();

      expect(() => {
        render(<TestComponent />);
      }).toThrow('useStaff must be used within StaffProvider');

      console.error = originalError;
    });

    test('provides context when used within provider', async () => {
      let contextValue;

      render(
        <MemoryRouter>
          <StaffProvider>
            <TestComponent onContextValue={(ctx) => (contextValue = ctx)} />
          </StaffProvider>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(contextValue).toBeDefined();
        expect(contextValue.library).toBeDefined();
        expect(contextValue.loadLibrary).toBeDefined();
        expect(contextValue.showToast).toBeDefined();
      });
    });
  });
});
