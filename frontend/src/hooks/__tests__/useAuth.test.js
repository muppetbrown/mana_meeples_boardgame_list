// frontend/src/hooks/__tests__/useAuth.test.js
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '../useAuth';
import * as apiClient from '../../api/client';

// Mock the API client
jest.mock('../../api/client', () => ({
  adminLogin: jest.fn(),
  validateAdminToken: jest.fn(),
  adminLogout: jest.fn(),
}));

// Mock safeStorage
jest.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('useAuth Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('initializes with not authenticated state', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));

    const { result } = renderHook(() => useAuth());

    // Initially validating
    expect(result.current.isValidating).toBe(true);

    // Wait for validation to complete
    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.error).toBeNull();
  });

  test('initializes as authenticated when token is valid', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
  });

  test('logs in successfully', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockResolvedValue({
      token: 'test-jwt-token',
      success: true
    });

    const { result } = renderHook(() => useAuth());

    // Wait for initial validation
    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    // Perform login
    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('test-admin-token');
    });

    expect(loginResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.error).toBeNull();
    expect(apiClient.adminLogin).toHaveBeenCalledWith('test-admin-token');
  });

  test('handles login failure with error message', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValue({
      response: { data: { detail: 'Invalid token' } }
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('bad-token');
    });

    expect(loginResult).toBe(false);
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.error).toBe('Invalid token');
  });

  test('handles login failure with generic error', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('bad-token');
    });

    expect(loginResult).toBe(false);
    expect(result.current.error).toBe('Network error');
  });

  test('logs out successfully', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockResolvedValue({ success: true });

    const { result } = renderHook(() => useAuth());

    // Wait for initial validation
    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    // Perform logout
    let logoutResult;
    await act(async () => {
      logoutResult = await result.current.logout();
    });

    expect(logoutResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.error).toBeNull();
    expect(apiClient.adminLogout).toHaveBeenCalled();
  });

  test('handles logout failure', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockRejectedValue({
      response: { data: { detail: 'Logout failed' } }
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    let logoutResult;
    await act(async () => {
      logoutResult = await result.current.logout();
    });

    expect(logoutResult).toBe(false);
    expect(result.current.error).toBe('Logout failed');
  });

  test('validates token on demand', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    // Mock successful validation
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });

    await act(async () => {
      await result.current.validate();
    });

    expect(result.current.isAuthenticated).toBe(true);
  });

  test('clears error on new login attempt', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValueOnce(new Error('First error'))
      .mockResolvedValueOnce({ token: 'test-token', success: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    // First login fails
    await act(async () => {
      await result.current.login('bad-token');
    });

    expect(result.current.error).toBe('First error');

    // Second login succeeds and clears error
    await act(async () => {
      await result.current.login('good-token');
    });

    expect(result.current.error).toBeNull();
    expect(result.current.isAuthenticated).toBe(true);
  });
});
