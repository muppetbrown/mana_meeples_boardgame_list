import { describe, test, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AdminToolsPanel } from '../AdminToolsPanel';
import * as apiClient from '../../../api/client';

// Mock the API client
vi.mock('../../../api/client', () => ({
  bulkUpdateNZDesigners: vi.fn(),
  bulkUpdateAfterGameIDs: vi.fn(),
  reimportAllGames: vi.fn(),
  fetchAllSleeveData: vi.fn(),
  backfillCloudinaryUrls: vi.fn(),
  fixDatabaseSequence: vi.fn(),
  getDebugCategories: vi.fn(),
  getDebugDatabaseInfo: vi.fn(),
  getDebugPerformance: vi.fn(),
  exportGamesCSV: vi.fn(),
  getHealthCheck: vi.fn(),
  getDbHealthCheck: vi.fn(),
}));

describe('AdminToolsPanel', () => {
  const mockToast = vi.fn();
  const mockLibraryReload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.confirm
    global.confirm = vi.fn(() => true);
    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  test('renders all sections', () => {
    render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

    expect(screen.getByText('Bulk Update NZ Designers')).toBeInTheDocument();
    expect(screen.getByText(/Bulk Update AfterGame IDs/)).toBeInTheDocument();
    expect(screen.getByText('Advanced Operations')).toBeInTheDocument();
    expect(screen.getByText('Debug & Monitoring')).toBeInTheDocument();
  });

  describe('Bulk NZ Designers Update', () => {
    test('shows error when CSV is empty', async () => {
      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Update NZ Designers/i });
      fireEvent.click(button);

      expect(mockToast).toHaveBeenCalledWith('Please enter CSV data', 'error');
    });

    test('handles successful bulk NZ designers update', async () => {
      apiClient.bulkUpdateNZDesigners.mockResolvedValue({
        updated: ['Game 1: False → True'],
        not_found: [],
        errors: [],
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const textarea = screen.getAllByRole('textbox')[0];
      fireEvent.change(textarea, { target: { value: '12345,true' } });

      const button = screen.getByRole('button', { name: /Update NZ Designers/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.bulkUpdateNZDesigners).toHaveBeenCalledWith('12345,true');
        expect(mockToast).toHaveBeenCalledWith(
          'Updated: 1, Not found: 0, Errors: 0',
          'success'
        );
        expect(mockLibraryReload).toHaveBeenCalled();
      });
    });

    test('handles failed bulk NZ designers update', async () => {
      apiClient.bulkUpdateNZDesigners.mockRejectedValue(new Error('Network error'));

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const textarea = screen.getAllByRole('textbox')[0];
      fireEvent.change(textarea, { target: { value: '12345,true' } });

      const button = screen.getByRole('button', { name: /Update NZ Designers/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith('Bulk NZ designers update failed', 'error');
      });
    });
  });

  describe('Bulk AfterGame IDs Update', () => {
    test('shows error when CSV is empty', async () => {
      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Update AfterGame IDs/i });
      fireEvent.click(button);

      expect(mockToast).toHaveBeenCalledWith('Please enter CSV data', 'error');
    });

    test('handles successful bulk AfterGame IDs update', async () => {
      apiClient.bulkUpdateAfterGameIDs.mockResolvedValue({
        updated: ['Game 1: None → abc-123'],
        not_found: [],
        errors: [],
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const textareas = screen.getAllByRole('textbox');
      const afterGameTextarea = textareas[1];
      fireEvent.change(afterGameTextarea, {
        target: { value: '12345,abc-123,Game 1' },
      });

      const button = screen.getByRole('button', { name: /Update AfterGame IDs/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.bulkUpdateAfterGameIDs).toHaveBeenCalledWith('12345,abc-123,Game 1');
        expect(mockToast).toHaveBeenCalledWith(
          'Updated: 1, Not found: 0, Errors: 0',
          'success'
        );
      });
    });
  });

  describe('Advanced Operations', () => {
    test('re-import all games with confirmation', async () => {
      apiClient.reimportAllGames.mockResolvedValue({
        updated: 50,
        errors: 0,
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Re-import All Games/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.confirm).toHaveBeenCalled();
        expect(apiClient.reimportAllGames).toHaveBeenCalled();
        expect(mockToast).toHaveBeenCalledWith(
          expect.stringContaining('Re-import complete'),
          'success'
        );
      });
    });

    test('cancels re-import when user cancels confirmation', async () => {
      global.confirm = vi.fn(() => false);

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Re-import All Games/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.confirm).toHaveBeenCalled();
        expect(apiClient.reimportAllGames).not.toHaveBeenCalled();
      });
    });

    test('fetches sleeve data with confirmation', async () => {
      apiClient.fetchAllSleeveData.mockResolvedValue({
        total_games: 100,
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Fetch Sleeve Data/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.confirm).toHaveBeenCalled();
        expect(apiClient.fetchAllSleeveData).toHaveBeenCalled();
        expect(mockToast).toHaveBeenCalledWith(
          expect.stringContaining('Processing 100 games'),
          'success'
        );
      });
    });

    test('fixes database sequence', async () => {
      apiClient.fixDatabaseSequence.mockResolvedValue({
        next_id: 501,
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Fix Database Sequence/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.fixDatabaseSequence).toHaveBeenCalled();
        expect(mockToast).toHaveBeenCalledWith(
          'Sequence fixed! Next ID will be: 501',
          'success'
        );
      });
    });

    test('exports games CSV', async () => {
      apiClient.exportGamesCSV.mockResolvedValue('id,title\n1,Catan\n2,Pandemic');

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Export Games CSV/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.exportGamesCSV).toHaveBeenCalled();
        expect(mockToast).toHaveBeenCalledWith('CSV exported successfully', 'success');
      });
    });

    test('backfills Cloudinary URLs', async () => {
      apiClient.backfillCloudinaryUrls.mockResolvedValue({
        updated: 50,
        skipped: 10,
        failed: 2,
        cloudinary_enabled: true,
        errors: ['Error 1', 'Error 2'],
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Backfill Cloudinary URLs/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(global.confirm).toHaveBeenCalled();
        expect(apiClient.backfillCloudinaryUrls).toHaveBeenCalled();
        expect(mockToast).toHaveBeenCalledWith(
          expect.stringContaining('Updated: 50'),
          'success',
          5000
        );
      });
    });
  });

  describe('Debug & Monitoring', () => {
    test('fetches system health', async () => {
      apiClient.getHealthCheck.mockResolvedValue({ status: 'ok' });
      apiClient.getDbHealthCheck.mockResolvedValue({ status: 'ok', game_count: 100 });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /System Health/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.getHealthCheck).toHaveBeenCalled();
        expect(apiClient.getDbHealthCheck).toHaveBeenCalled();
      });
    });

    test('fetches performance stats', async () => {
      apiClient.getDebugPerformance.mockResolvedValue({
        avg_response_time: 50,
        requests: 1000,
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Performance Stats/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.getDebugPerformance).toHaveBeenCalled();
      });
    });

    test('fetches database info', async () => {
      apiClient.getDebugDatabaseInfo.mockResolvedValue({
        tables: ['boardgames', 'sleeves'],
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /Database Info/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.getDebugDatabaseInfo).toHaveBeenCalledWith(100);
      });
    });

    test('fetches BGG categories', async () => {
      apiClient.getDebugCategories.mockResolvedValue({
        categories: ['Strategy', 'Family'],
      });

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /BGG Categories/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(apiClient.getDebugCategories).toHaveBeenCalled();
      });
    });

    test('handles debug info fetch error', async () => {
      apiClient.getDebugCategories.mockRejectedValue(new Error('Network error'));

      render(<AdminToolsPanel onToast={mockToast} onLibraryReload={mockLibraryReload} />);

      const button = screen.getByRole('button', { name: /BGG Categories/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith('Failed to get categories info', 'error');
      });
    });
  });
});
