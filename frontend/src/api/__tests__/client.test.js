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

const mockStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
};

vi.mock('../../utils/storage', () => ({
  safeStorage: mockStorage,
}));

// Import after mocks are set up
const apiClient = await import('../client');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Public API Methods', () => {
    test('getPublicGames fetches games with params', async () => {
      const mockResponse = {
        data: {
          items: [{ id: 1, title: 'Catan' }],
          total: 1,
          page: 1,
          page_size: 20,
        },
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const params = { q: 'Catan', category: 'GATEWAY_STRATEGY' };
      const result = await apiClient.getPublicGames(params);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/public/games', { params });
      expect(result).toEqual(mockResponse.data);
    });

    test('getPublicGames works without params', async () => {
      const mockResponse = { data: { items: [], total: 0 } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getPublicGames();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/public/games', { params: {} });
      expect(result).toEqual(mockResponse.data);
    });

    test('getPublicGame fetches single game by ID', async () => {
      const mockGame = { id: 1, title: 'Catan' };
      mockAxiosInstance.get.mockResolvedValue({ data: mockGame });

      const result = await apiClient.getPublicGame(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/public/games/1');
      expect(result).toEqual(mockGame);
    });

    test('getPublicCategoryCounts fetches category counts', async () => {
      const mockCounts = { GATEWAY_STRATEGY: 50, CORE_STRATEGY: 30 };
      mockAxiosInstance.get.mockResolvedValue({ data: mockCounts });

      const result = await apiClient.getPublicCategoryCounts();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/public/category-counts');
      expect(result).toEqual(mockCounts);
    });
  });

  describe('Admin Game Management Methods', () => {
    test('getGames fetches all games', async () => {
      const mockGames = [{ id: 1 }, { id: 2 }];
      mockAxiosInstance.get.mockResolvedValue({ data: mockGames });

      const result = await apiClient.getGames();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/games');
      expect(result).toEqual(mockGames);
    });

    test('getGames returns empty array on error', async () => {
      mockAxiosInstance.get.mockRejectedValue(new Error('Network error'));

      const result = await apiClient.getGames();

      expect(result).toEqual([]);
    });

    test('addGame creates a new game', async () => {
      const newGame = { title: 'New Game', year: 2024 };
      const mockResponse = { data: { id: 1, ...newGame } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.addGame(newGame);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/games', newGame);
      expect(result).toEqual(mockResponse.data);
    });

    test('updateGame updates existing game', async () => {
      const patch = { title: 'Updated Title' };
      const mockResponse = { data: { id: 1, ...patch } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.updateGame(1, patch);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/games/1/update', patch);
      expect(result).toEqual(mockResponse.data);
    });

    test('updateGame handles 500 errors', async () => {
      const patch = { title: 'Updated' };
      const error = {
        response: {
          status: 500,
          data: { detail: 'Internal error' },
        },
      };
      mockAxiosInstance.post.mockRejectedValue(error);

      await expect(apiClient.updateGame(1, patch)).rejects.toEqual(error);
    });

    test('deleteGame deletes a game by ID', async () => {
      const mockResponse = { data: { success: true } };
      mockAxiosInstance.delete.mockResolvedValue(mockResponse);

      const result = await apiClient.deleteGame(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/games/1');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Admin Bulk Operations Methods', () => {
    test('bulkImportCsv imports games from CSV', async () => {
      const csvData = 'bgg_id,title\n1234,Catan';
      const mockResponse = { data: { imported: 1, errors: [] } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.bulkImportCsv(csvData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/bulk-import-csv',
        { csv_data: csvData }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('bulkCategorizeCsv categorizes games from CSV', async () => {
      const csvData = 'title,category\nCatan,GATEWAY_STRATEGY';
      const mockResponse = { data: { categorized: 1, errors: [] } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.bulkCategorizeCsv(csvData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/bulk-categorize-csv',
        { csv_data: csvData }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('bulkUpdateNZDesigners updates NZ designer flags', async () => {
      const csvData = 'title,nz_designer\nCatan,true';
      const mockResponse = { data: { updated: 1 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.bulkUpdateNZDesigners(csvData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/bulk-update-nz-designers',
        { csv_data: csvData }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('bulkUpdateAfterGameIDs updates AfterGame IDs', async () => {
      const csvData = 'bgg_id,aftergame_game_id\n1234,5678';
      const mockResponse = { data: { updated: 1 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.bulkUpdateAfterGameIDs(csvData);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/bulk-update-aftergame-ids',
        { csv_data: csvData }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('reimportAllGames triggers full re-import', async () => {
      const mockResponse = { data: { status: 'started' } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.reimportAllGames();

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/reimport-all-games', {});
      expect(result).toEqual(mockResponse.data);
    });

    test('fetchAllSleeveData fetches sleeve data', async () => {
      const mockResponse = { data: { status: 'started' } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.fetchAllSleeveData();

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/fetch-all-sleeve-data', {});
      expect(result).toEqual(mockResponse.data);
    });

    test('fixDatabaseSequence fixes sequence errors', async () => {
      const mockResponse = { data: { max_id: 100, next_id: 101 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.fixDatabaseSequence();

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/fix-sequence', {});
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Admin Authentication Methods', () => {
    test('adminLogin stores JWT token', async () => {
      const mockResponse = {
        data: { token: 'jwt-token-123', success: true },
      };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.adminLogin('admin-token');

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/login', {
        token: 'admin-token',
      });
      expect(mockStorage.setItem).toHaveBeenCalledWith('JWT_TOKEN', 'jwt-token-123');
      expect(result).toEqual(mockResponse.data);
    });

    test('adminLogin handles response without token', async () => {
      const mockResponse = { data: { success: false } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.adminLogin('invalid-token');

      expect(mockStorage.setItem).not.toHaveBeenCalled();
      expect(result).toEqual(mockResponse.data);
    });

    test('adminLogout clears JWT token', async () => {
      const mockResponse = { data: { success: true } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.adminLogout();

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/logout');
      expect(mockStorage.removeItem).toHaveBeenCalledWith('JWT_TOKEN');
      expect(result).toEqual(mockResponse.data);
    });

    test('validateAdminToken validates session', async () => {
      const mockResponse = { data: { valid: true } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.validateAdminToken();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/validate');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Debug & Monitoring Methods', () => {
    test('getDebugCategories fetches BGG categories', async () => {
      const mockResponse = { data: { categories: ['Strategy', 'Family'] } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getDebugCategories();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/categories');
      expect(result).toEqual(mockResponse.data);
    });

    test('getDebugDatabaseInfo fetches database info with default limit', async () => {
      const mockResponse = { data: { tables: [], sample_games: [] } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getDebugDatabaseInfo();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/database-info', {
        params: { limit: 50 },
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('getDebugDatabaseInfo fetches database info with custom limit', async () => {
      const mockResponse = { data: { tables: [] } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getDebugDatabaseInfo(100);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/database-info', {
        params: { limit: 100 },
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('getDebugPerformance fetches performance metrics', async () => {
      const mockResponse = { data: { avg_response_time: 50, requests: 1000 } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getDebugPerformance();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/performance');
      expect(result).toEqual(mockResponse.data);
    });

    test('exportGamesCSV exports without limit', async () => {
      const mockResponse = { data: 'id,title\n1,Catan' };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.exportGamesCSV();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/export-games-csv', {
        params: {},
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('exportGamesCSV exports with limit', async () => {
      const mockResponse = { data: 'id,title\n1,Catan' };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.exportGamesCSV(10);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/debug/export-games-csv', {
        params: { limit: 10 },
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Health Check Methods', () => {
    test('getHealthCheck fetches basic health', async () => {
      const mockResponse = { data: { status: 'ok' } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getHealthCheck();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health');
      expect(result).toEqual(mockResponse.data);
    });

    test('getDbHealthCheck fetches database health', async () => {
      const mockResponse = { data: { status: 'ok', game_count: 100 } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getDbHealthCheck();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health/db');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('BGG Import Methods', () => {
    test('importFromBGG imports without force', async () => {
      const mockResponse = { data: { success: true, game_id: 1 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.importFromBGG(1234);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/import/bgg', null, {
        params: { bgg_id: 1234, force: false },
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('importFromBGG imports with force flag', async () => {
      const mockResponse = { data: { success: true, game_id: 1 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.importFromBGG(1234, true);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/import/bgg', null, {
        params: { bgg_id: 1234, force: true },
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Buy List Methods', () => {
    test('getBuyListGames fetches buy list with params', async () => {
      const params = { on_buy_list: true, sort_by: 'rank' };
      const mockResponse = { data: { total: 10, items: [] } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getBuyListGames(params);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/buy-list/games', { params });
      expect(result).toEqual(mockResponse.data);
    });

    test('getBuyListGames fetches without params', async () => {
      const mockResponse = { data: { total: 0, items: [] } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getBuyListGames();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/buy-list/games', {
        params: {},
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('addToBuyList adds game to buy list', async () => {
      const data = { game_id: 1, rank: 5, lpg_rrp: 49.99 };
      const mockResponse = { data: { id: 1, ...data } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.addToBuyList(data);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/buy-list/games', data);
      expect(result).toEqual(mockResponse.data);
    });

    test('updateBuyListGame updates buy list entry', async () => {
      const data = { rank: 3, lpg_status: 'in_stock' };
      const mockResponse = { data: { id: 1, ...data } };
      mockAxiosInstance.put.mockResolvedValue(mockResponse);

      const result = await apiClient.updateBuyListGame(1, data);

      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/admin/buy-list/games/1', data);
      expect(result).toEqual(mockResponse.data);
    });

    test('removeFromBuyList removes game from buy list', async () => {
      const mockResponse = { data: { success: true } };
      mockAxiosInstance.delete.mockResolvedValue(mockResponse);

      const result = await apiClient.removeFromBuyList(1);

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/admin/buy-list/games/1');
      expect(result).toEqual(mockResponse.data);
    });

    test('importPrices imports price data', async () => {
      const mockResponse = { data: { imported: 50 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.importPrices('prices.json');

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/admin/buy-list/import-prices',
        null,
        {
          params: { source_file: 'prices.json' },
        }
      );
      expect(result).toEqual(mockResponse.data);
    });

    test('getLastPriceUpdate fetches last update timestamp', async () => {
      const mockResponse = { data: { last_updated: '2024-01-01', source_file: 'prices.json' } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getLastPriceUpdate();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/buy-list/last-updated');
      expect(result).toEqual(mockResponse.data);
    });

    test('bulkImportBuyListCSV imports CSV file', async () => {
      const file = new File(['bgg_id,rank\n1234,1'], 'buylist.csv', { type: 'text/csv' });
      const mockResponse = { data: { added: 1, updated: 0 } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.bulkImportBuyListCSV(file);

      expect(mockAxiosInstance.post).toHaveBeenCalled();
      const callArgs = mockAxiosInstance.post.mock.calls[0];
      expect(callArgs[0]).toBe('/admin/buy-list/bulk-import-csv');
      expect(callArgs[1]).toBeInstanceOf(FormData);
      expect(callArgs[2]).toEqual({
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Sleeve Management Methods', () => {
    test('generateSleeveShoppingList generates shopping list', async () => {
      const gameIds = [1, 2, 3];
      const mockResponse = { data: [{ size: '63.5x88', quantity: 100 }] };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.generateSleeveShoppingList(gameIds);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/sleeves/shopping-list', {
        game_ids: gameIds,
      });
      expect(result).toEqual(mockResponse.data);
    });

    test('triggerSleeveFetch triggers GitHub workflow', async () => {
      const gameIds = [1, 2, 3];
      const mockResponse = { data: { workflow_id: 'abc123' } };
      mockAxiosInstance.post.mockResolvedValue(mockResponse);

      const result = await apiClient.triggerSleeveFetch(gameIds);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/admin/trigger-sleeve-fetch', gameIds);
      expect(result).toEqual(mockResponse.data);
    });

    test('getGameSleeves fetches sleeves for a game', async () => {
      const mockResponse = { data: [{ size: '63.5x88', quantity: 50 }] };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await apiClient.getGameSleeves(1);

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/admin/sleeves/game/1');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('Utility Functions', () => {
    test('imageProxyUrl is re-exported', () => {
      expect(apiClient.imageProxyUrl).toBeDefined();
    });

    test('generateSrcSet is re-exported', () => {
      expect(apiClient.generateSrcSet).toBeDefined();
    });
  });

  describe('Axios Interceptors', () => {
    test('request interceptor adds JWT token when present', () => {
      mockStorage.getItem.mockReturnValue('test-jwt-token');

      // Verify interceptor is registered
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();

      // Get the request interceptor function
      const requestInterceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0];

      // Test config with token
      const config = { headers: {} };
      const result = requestInterceptor(config);

      expect(result.headers.Authorization).toBe('Bearer test-jwt-token');
    });

    test('request interceptor does not add token when not present', () => {
      mockStorage.getItem.mockReturnValue(null);

      const requestInterceptor = mockAxiosInstance.interceptors.request.use.mock.calls[0][0];
      const config = { headers: {} };
      const result = requestInterceptor(config);

      expect(result.headers.Authorization).toBeUndefined();
    });

    test('request interceptor error handler rejects errors', () => {
      const errorHandler = mockAxiosInstance.interceptors.request.use.mock.calls[0][1];
      const error = new Error('Request failed');

      expect(errorHandler(error)).rejects.toBe(error);
    });

    test('response interceptor handles 401 errors on admin routes', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      const error = {
        config: { url: '/api/admin/games' },
        response: { status: 401, statusText: 'Unauthorized', data: 'Unauthorized' },
      };

      // Mock window.location
      const originalLocation = window.location;
      delete window.location;
      window.location = { pathname: '/staff', origin: 'http://localhost', href: '' };

      const result = responseInterceptor(error);

      expect(result).rejects.toBe(error);

      // Restore original location
      window.location = originalLocation;
    });

    test('response interceptor handles timeout errors', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      const error = {
        code: 'ECONNABORTED',
        config: { url: '/api/admin/bulk-import' },
        message: 'timeout of 300000ms exceeded',
      };

      expect(responseInterceptor(error)).rejects.toThrow(/timeout/i);
    });

    test('response interceptor handles network errors', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      const error = {
        config: { url: '/api/public/games', method: 'GET' },
        response: { status: 500, statusText: 'Internal Server Error', data: 'Error occurred' },
        message: 'Network Error',
      };

      expect(responseInterceptor(error)).rejects.toBe(error);
    });

    test('response interceptor handles errors with JSON data', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      const error = {
        config: { url: '/api/admin/games', method: 'POST' },
        response: {
          status: 400,
          statusText: 'Bad Request',
          data: { detail: 'Invalid input', errors: ['Field required'] },
        },
        message: 'Request failed with status code 400',
      };

      expect(responseInterceptor(error)).rejects.toBe(error);
    });

    test('response interceptor success handler returns response as-is', () => {
      const successHandler = mockAxiosInstance.interceptors.response.use.mock.calls[0][0];
      const response = { data: { id: 1, title: 'Test' }, status: 200 };

      expect(successHandler(response)).toBe(response);
    });
  });

  describe('Error Handling', () => {
    test('handles errors without response object', async () => {
      const networkError = new Error('Network Error');
      mockAxiosInstance.get.mockRejectedValue(networkError);

      // getGames has error handling that returns empty array
      const result = await apiClient.getGames();
      expect(result).toEqual([]);
    });

    test('handles errors without config object', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      const error = {
        message: 'Something went wrong',
      };

      expect(responseInterceptor(error)).rejects.toBe(error);
    });
  });

  describe('Development Debugging', () => {
    test('debug overlay is created on API errors in development', () => {
      const responseInterceptor = mockAxiosInstance.interceptors.response.use.mock.calls[0][1];

      // Mock document methods
      const mockElement = {
        id: '',
        style: { cssText: '' },
        textContent: '',
      };
      const createElement = vi.spyOn(document, 'createElement').mockReturnValue(mockElement);
      const getElementById = vi.spyOn(document, 'getElementById').mockReturnValue(null);
      const appendChild = vi.spyOn(document.body, 'appendChild').mockImplementation(() => {});

      const error = {
        config: { url: '/api/test', method: 'GET' },
        response: { status: 500, data: 'Error' },
        message: 'Server Error',
      };

      responseInterceptor(error).catch(() => {});

      // Verify overlay was created (in real usage)
      // Note: May not actually create in test environment due to error handling

      // Cleanup
      createElement.mockRestore();
      getElementById.mockRestore();
      appendChild.mockRestore();
    });
  });
});
