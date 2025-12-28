// frontend/src/api/__tests__/client.test.js
import axios from 'axios';
import {
  getPublicGames,
  getPublicGame,
  getPublicCategoryCounts,
  getGames,
  addGame,
  updateGame,
  deleteGame,
  adminLogin,
  adminLogout,
  validateAdminToken,
  bulkImportCsv,
  bulkCategorizeCsv,
  bulkUpdateNZDesigners,
  importFromBGG,
} from '../client';

jest.mock('axios');

// Mock safeStorage
jest.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock axios.create to return a mocked axios instance
    axios.create.mockReturnValue(axios);
  });

  describe('Public API Methods', () => {
    describe('getPublicGames', () => {
      test('fetches games successfully with filters', async () => {
        const mockResponse = {
          data: {
            items: [
              { id: 1, title: 'Catan' },
              { id: 2, title: 'Pandemic' },
            ],
            total: 2,
            page: 1,
            page_size: 12,
          },
        };
        axios.get.mockResolvedValue(mockResponse);

        const result = await getPublicGames({ q: 'Catan', category: 'STRATEGY' });

        expect(axios.get).toHaveBeenCalledWith('/api/public/games', {
          params: { q: 'Catan', category: 'STRATEGY' },
        });
        expect(result).toEqual(mockResponse.data);
      });

      test('handles errors', async () => {
        axios.get.mockRejectedValue(new Error('Network error'));

        await expect(getPublicGames()).rejects.toThrow('Network error');
      });
    });

    describe('getPublicGame', () => {
      test('fetches single game successfully', async () => {
        const mockGame = { id: 1, title: 'Catan', players_min: 3 };
        axios.get.mockResolvedValue({ data: mockGame });

        const result = await getPublicGame(1);

        expect(axios.get).toHaveBeenCalledWith('/api/public/games/1');
        expect(result).toEqual(mockGame);
      });

      test('handles not found error', async () => {
        axios.get.mockRejectedValue({
          response: { status: 404, data: { detail: 'Game not found' } },
        });

        await expect(getPublicGame(999)).rejects.toMatchObject({
          response: { status: 404 },
        });
      });
    });

    describe('getPublicCategoryCounts', () => {
      test('fetches category counts successfully', async () => {
        const mockCounts = {
          GATEWAY_STRATEGY: 50,
          COOP_ADVENTURE: 30,
          CORE_STRATEGY: 40,
          KIDS_FAMILIES: 25,
          PARTY_ICEBREAKERS: 20,
        };
        axios.get.mockResolvedValue({ data: mockCounts });

        const result = await getPublicCategoryCounts();

        expect(axios.get).toHaveBeenCalledWith('/api/public/category-counts');
        expect(result).toEqual(mockCounts);
      });
    });
  });

  describe('Admin Game Management Methods', () => {
    describe('getGames', () => {
      test('fetches all games successfully', async () => {
        const mockGames = [
          { id: 1, title: 'Game 1' },
          { id: 2, title: 'Game 2' },
        ];
        axios.get.mockResolvedValue({ data: mockGames });

        const result = await getGames();

        expect(axios.get).toHaveBeenCalledWith('/api/admin/games');
        expect(result).toEqual(mockGames);
      });

      test('returns empty array on error', async () => {
        const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
        axios.get.mockRejectedValue(new Error('Network error'));

        const result = await getGames();

        expect(result).toEqual([]);
        expect(consoleErrorSpy).toHaveBeenCalledWith('Failed to load games:', expect.any(Error));
        consoleErrorSpy.mockRestore();
      });
    });

    describe('addGame', () => {
      test('creates new game successfully', async () => {
        const newGame = { title: 'New Game', year: 2024 };
        const createdGame = { id: 1, ...newGame };
        axios.post.mockResolvedValue({ data: createdGame });

        const result = await addGame(newGame);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/games', newGame);
        expect(result).toEqual(createdGame);
      });

      test('handles validation errors', async () => {
        axios.post.mockRejectedValue({
          response: { status: 400, data: { detail: 'Validation error' } },
        });

        await expect(addGame({})).rejects.toMatchObject({
          response: { status: 400 },
        });
      });
    });

    describe('updateGame', () => {
      test('updates game successfully', async () => {
        const updatedGame = { id: 1, title: 'Updated Game' };
        axios.post.mockResolvedValue({ data: updatedGame });

        const result = await updateGame(1, { title: 'Updated Game' });

        expect(axios.post).toHaveBeenCalledWith('/api/admin/games/1/update', {
          title: 'Updated Game',
        });
        expect(result).toEqual(updatedGame);
      });

      test('handles 500 errors with warning', async () => {
        const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
        const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();

        axios.post.mockRejectedValue({
          response: { status: 500, data: { detail: 'Server error' } },
        });

        await expect(updateGame(1, { title: 'Test' })).rejects.toMatchObject({
          response: { status: 500 },
        });

        expect(consoleWarnSpy).toHaveBeenCalled();
        consoleWarnSpy.mockRestore();
        consoleLogSpy.mockRestore();
      });
    });

    describe('deleteGame', () => {
      test('deletes game successfully', async () => {
        const deleteResponse = { success: true, message: 'Game deleted' };
        axios.delete.mockResolvedValue({ data: deleteResponse });

        const result = await deleteGame(1);

        expect(axios.delete).toHaveBeenCalledWith('/api/admin/games/1');
        expect(result).toEqual(deleteResponse);
      });
    });
  });

  describe('Authentication Methods', () => {
    describe('adminLogin', () => {
      test('logs in successfully and stores token', async () => {
        const mockResponse = {
          data: { token: 'test-jwt-token', success: true },
        };
        axios.post.mockResolvedValue(mockResponse);

        const { safeStorage } = require('../../utils/storage');

        const result = await adminLogin('admin-token');

        expect(axios.post).toHaveBeenCalledWith('/api/admin/login', {
          token: 'admin-token',
        });
        expect(result).toEqual(mockResponse.data);
        expect(safeStorage.setItem).toHaveBeenCalledWith('JWT_TOKEN', 'test-jwt-token');
      });

      test('handles login failure', async () => {
        axios.post.mockRejectedValue({
          response: { status: 401, data: { detail: 'Invalid credentials' } },
        });

        await expect(adminLogin('bad-token')).rejects.toMatchObject({
          response: { status: 401 },
        });
      });
    });

    describe('adminLogout', () => {
      test('logs out successfully and clears token', async () => {
        const mockResponse = { data: { success: true } };
        axios.post.mockResolvedValue(mockResponse);

        const { safeStorage } = require('../../utils/storage');

        const result = await adminLogout();

        expect(axios.post).toHaveBeenCalledWith('/api/admin/logout');
        expect(result).toEqual(mockResponse.data);
        expect(safeStorage.removeItem).toHaveBeenCalledWith('JWT_TOKEN');
      });
    });

    describe('validateAdminToken', () => {
      test('validates token successfully', async () => {
        const mockResponse = { data: { valid: true } };
        axios.get.mockResolvedValue(mockResponse);

        const result = await validateAdminToken();

        expect(axios.get).toHaveBeenCalledWith('/api/admin/validate');
        expect(result).toEqual(mockResponse.data);
      });

      test('handles invalid token', async () => {
        axios.get.mockRejectedValue({
          response: { status: 401, data: { detail: 'Invalid token' } },
        });

        await expect(validateAdminToken()).rejects.toMatchObject({
          response: { status: 401 },
        });
      });
    });
  });

  describe('Bulk Operations', () => {
    describe('bulkImportCsv', () => {
      test('imports games from CSV successfully', async () => {
        const mockResponse = {
          data: { added: 5, updated: 2, skipped: 1 },
        };
        axios.post.mockResolvedValue(mockResponse);

        const csvData = 'bgg_id,title\n123,Catan\n456,Pandemic';
        const result = await bulkImportCsv(csvData);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/bulk-import-csv', {
          csv_data: csvData,
        });
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('bulkCategorizeCsv', () => {
      test('categorizes games from CSV successfully', async () => {
        const mockResponse = {
          data: { updated: 10, skipped: 2 },
        };
        axios.post.mockResolvedValue(mockResponse);

        const csvData = 'bgg_id,category\n123,STRATEGY\n456,PARTY';
        const result = await bulkCategorizeCsv(csvData);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/bulk-categorize-csv', {
          csv_data: csvData,
        });
        expect(result).toEqual(mockResponse.data);
      });
    });

    describe('bulkUpdateNZDesigners', () => {
      test('updates NZ designer flags from CSV successfully', async () => {
        const mockResponse = {
          data: { updated: 15 },
        };
        axios.post.mockResolvedValue(mockResponse);

        const csvData = 'bgg_id,nz_designer\n123,true\n456,false';
        const result = await bulkUpdateNZDesigners(csvData);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/bulk-update-nz-designers', {
          csv_data: csvData,
        });
        expect(result).toEqual(mockResponse.data);
      });
    });
  });

  describe('BGG Integration', () => {
    describe('importFromBGG', () => {
      test('imports game from BGG successfully', async () => {
        const mockGame = { id: 1, title: 'Catan', bgg_id: 123 };
        axios.post.mockResolvedValue({ data: mockGame });

        const result = await importFromBGG(123, false);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/import/bgg', null, {
          params: { bgg_id: 123, force: false },
        });
        expect(result).toEqual(mockGame);
      });

      test('imports with force flag', async () => {
        const mockGame = { id: 1, title: 'Catan', bgg_id: 123 };
        axios.post.mockResolvedValue({ data: mockGame });

        await importFromBGG(123, true);

        expect(axios.post).toHaveBeenCalledWith('/api/admin/import/bgg', null, {
          params: { bgg_id: 123, force: true },
        });
      });
    });
  });
});
