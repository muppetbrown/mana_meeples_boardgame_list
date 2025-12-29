// frontend/src/hooks/__tests__/useAuth.test.js
import { describe, test, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '../useAuth';
import * as apiClient from '../../api/client';

// Mock the API client
vi.mock('../../api/client', () => ({
  adminLogin: vi.fn(),
  validateAdminToken: vi.fn(),
  adminLogout: vi.fn(),
}));

// Mock safeStorage
vi.mock('../../utils/storage', () => ({
  safeStorage: {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  },
}));

describe('useAuth Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('initializes with not authenticated state', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
  });

  test('logs in successfully', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockResolvedValue({
      token: 'test-jwt-token',
      success: true
    });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('test-admin-token');
    });

    expect(loginResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(true);
  });

  test('handles login failure', async () => {
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
    expect(result.current.error).toBe('Invalid token');
  });

  test('logs out successfully', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockResolvedValue({ success: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    let logoutResult;
    await act(async () => {
      logoutResult = await result.current.logout();
    });

    expect(logoutResult).toBe(true);
    expect(result.current.isAuthenticated).toBe(false);
  });

  test('handles logout failure with response.data.detail', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockRejectedValue({
      response: { data: { detail: 'Session expired' } }
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
    expect(result.current.error).toBe('Session expired');
  });

  test('handles logout failure with err.message fallback', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    let logoutResult;
    await act(async () => {
      logoutResult = await result.current.logout();
    });

    expect(logoutResult).toBe(false);
    expect(result.current.error).toBe('Network error');
  });

  test('handles logout failure with default message', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    // Reject with an object that has no message or response
    apiClient.adminLogout.mockRejectedValue({});

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

  test('handles login failure with err.message fallback', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValue(new Error('Connection timeout'));

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('test-token');
    });

    expect(loginResult).toBe(false);
    expect(result.current.error).toBe('Connection timeout');
  });

  test('handles login failure with default message', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    // Reject with an object that has no message or response
    apiClient.adminLogin.mockRejectedValue({});

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    let loginResult;
    await act(async () => {
      loginResult = await result.current.login('test-token');
    });

    expect(loginResult).toBe(false);
    expect(result.current.error).toBe('Login failed');
  });

  test('validates authentication on mount', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });

    const { result } = renderHook(() => useAuth());

    // Should start validating
    expect(result.current.isValidating).toBe(true);

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(apiClient.validateAdminToken).toHaveBeenCalled();
  });

  test('clears error when calling login', async () => {
    apiClient.validateAdminToken.mockRejectedValue(new Error('Not authenticated'));
    apiClient.adminLogin.mockRejectedValueOnce(new Error('First failure'))
                       .mockResolvedValueOnce({ token: 'jwt-token', success: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    // First login fails
    await act(async () => {
      await result.current.login('bad-token');
    });

    expect(result.current.error).toBe('First failure');

    // Second login succeeds
    await act(async () => {
      await result.current.login('good-token');
    });

    // Error should be cleared
    expect(result.current.error).toBeNull();
    expect(result.current.isAuthenticated).toBe(true);
  });

  test('clears error when calling logout', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });
    apiClient.adminLogout.mockResolvedValue({ success: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    // Manually set an error
    await act(async () => {
      result.current.login('bad-token');
    });

    // Now logout successfully
    await act(async () => {
      await result.current.logout();
    });

    // Error should be cleared
    expect(result.current.error).toBeNull();
  });

  test('clears error when calling validate', async () => {
    apiClient.validateAdminToken.mockResolvedValue({ valid: true });

    const { result } = renderHook(() => useAuth());

    await waitFor(() => {
      expect(result.current.isValidating).toBe(false);
    });

    // Manually set error state (simulate previous error)
    await act(async () => {
      result.current.login('bad-token');
    });

    // Call validate
    await act(async () => {
      await result.current.validate();
    });

    // Error should be cleared
    expect(result.current.error).toBeNull();
  });
});
