// frontend/src/api/__tests__/client.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';
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
  importFromBGG,
} from '../client';

vi.mock('axios');

// Mock safeStorage  
vi.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
}));

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    axios.create.mockReturnValue(axios);
  });

  describe('Public API Methods', () => {
    test('fetches games successfully', async () => {
      const mockResponse = {
        data: {
          items: [{ id: 1, title: 'Catan' }],
          total: 1,
        },
      };
      axios.get.mockResolvedValue(mockResponse);

      const result = await getPublicGames({ q: 'Catan' });

      expect(axios.get).toHaveBeenCalled();
      expect(result).toEqual(mockResponse.data);
    });

    test('fetches single game', async () => {
      const mockGame = { id: 1, title: 'Catan' };
      axios.get.mockResolvedValue({ data: mockGame });

      const result = await getPublicGame(1);

      expect(result).toEqual(mockGame);
    });

    test('fetches category counts', async () => {
      const mockCounts = { GATEWAY_STRATEGY: 50 };
      axios.get.mockResolvedValue({ data: mockCounts });

      const result = await getPublicCategoryCounts();

      expect(result).toEqual(mockCounts);
    });
  });

  describe('Admin Methods', () => {
    test('admin login stores token', async () => {
      const mockResponse = {
        data: { token: 'test-token', success: true },
      };
      axios.post.mockResolvedValue(mockResponse);

      const result = await adminLogin('admin-token');

      expect(result.token).toBe('test-token');
    });

    test('creates game', async () => {
      const newGame = { title: 'New Game' };
      axios.post.mockResolvedValue({ data: { id: 1, ...newGame } });

      const result = await addGame(newGame);

      expect(result.id).toBe(1);
    });

    test('imports from BGG', async () => {
      const mockGame = { id: 1, bgg_id: 123 };
      axios.post.mockResolvedValue({ data: mockGame });

      const result = await importFromBGG(123, false);

      expect(result).toEqual(mockGame);
    });
  });
});
