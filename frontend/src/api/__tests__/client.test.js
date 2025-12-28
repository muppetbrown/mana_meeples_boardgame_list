// frontend/src/api/__tests__/client.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';

// Create axios mock before importing client
const mockAxiosInstance = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: { use: vi.fn(), eject: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn() },
  },
};

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
    ...mockAxiosInstance,
  },
}));

vi.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
}));

// Import after mocks are set up
const apiClient = await import('../client');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Public API Methods', () => {
    test('fetches games successfully', async () => {
      const mockResponse = {
        data: {
          items: [{ id: 1, title: 'Catan' }],
          total: 1,
        },
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getPublicGames({ q: 'Catan' });

      expect(mockAxiosInstance.get).toHaveBeenCalled();
      expect(result).toEqual(mockResponse.data);
    });

    test('fetches single game', async () => {
      const mockGame = { id: 1, title: 'Catan' };
      mockAxiosInstance.get.mockResolvedValue({ data: mockGame });

      const result = await apiClient.getPublicGame(1);

      expect(result).toEqual(mockGame);
    });

    test('fetches category counts', async () => {
      const mockCounts = { GATEWAY_STRATEGY: 50 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockCounts });

      const result = await apiClient.getPublicCategoryCounts();

      expect(result).toEqual(mockCounts);
    });
  });

  describe('Admin Methods', () => {
    test('admin login stores token', async () => {
      const mockResponse = {
        data: { token: 'test-token', success: true },
      };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.adminLogin('admin-token');

      expect(result.token).toBe('test-token');
    });

    test('creates game', async () => {
      const newGame = { title: 'New Game' };
      mockAxiosInstance.post.mockResolvedValue({ data: { id: 1, ...newGame } });

      const result = await apiClient.addGame(newGame);

      expect(result.id).toBe(1);
    });
  });
});
